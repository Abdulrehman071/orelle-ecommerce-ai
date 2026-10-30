"""Sales analytics. EVERY number comes from the database through this code - the LLM only words the findings.

Definitions (also shown in the README):
  * An order counts toward sales unless its status is 'cancelled'.
  * revenue = sum of order.total (items + shipping - discount) = what the customer was charged.
  * Dates are inclusive, in the business time zone (Asia/Karachi); the DB stores UTC.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import func, select

from ..models_store import Order, OrderItem, Product, Variant
from ..timeutil import business_tz, local_bounds_to_utc, to_local_date
from .base import ADMIN_ONLY, STAFF, StrictModel, ToolContext, ToolError, money, tool

MAX_DAYS = 366


class RangeArgs(StrictModel):
    start_date: dt.date = Field(..., description="First day, YYYY-MM-DD (inclusive)")
    end_date: dt.date = Field(..., description="Last day, YYYY-MM-DD (inclusive)")

    @model_validator(mode="after")
    def _check(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days >= MAX_DAYS:
            raise ValueError(f"date range may not exceed {MAX_DAYS} days")
        return self


def _bounds(ctx: ToolContext, start: dt.date, end: dt.date):
    return local_bounds_to_utc(start, end, business_tz(ctx.settings))


def _pct_change(cur: Decimal, prev: Decimal):
    return None if prev == 0 else round(float((cur - prev) / prev * 100), 1)


def _summary(ctx: ToolContext, start: dt.date, end: dt.date) -> dict:
    a, b = _bounds(ctx, start, end)
    base = (Order.created_at >= a, Order.created_at < b)
    rows = ctx.store.execute(select(Order.status, Order.subtotal, Order.shipping_fee, Order.discount_amount,
                                    Order.total).where(*base)).all()
    by_status: dict[str, int] = defaultdict(int)
    revenue = subtotal = shipping = discounts = Decimal(0)
    n = 0
    for status, sub, ship, disc, total in rows:
        by_status[status] += 1
        if status == "cancelled":
            continue
        n += 1
        revenue += total; subtotal += sub; shipping += ship; discounts += disc
    units = ctx.store.execute(
        select(func.coalesce(func.sum(OrderItem.quantity), 0)).join(Order, OrderItem.order_id == Order.id)
        .where(*base, Order.status != "cancelled")
    ).scalar_one()
    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(), "currency": ctx.settings.currency,
        "orders": n, "revenue": money(revenue), "items_subtotal": money(subtotal),
        "shipping_collected": money(shipping), "discounts_given": money(discounts), "units_sold": int(units),
        "average_order_value": money(revenue / n) if n else None,
        "cancelled_orders": by_status.get("cancelled", 0), "orders_by_status": dict(sorted(by_status.items())),
        "_revenue_raw": revenue,
    }


def _public(summary: dict) -> dict:
    return {k: v for k, v in summary.items() if not k.startswith("_")}


def _best_sellers(ctx: ToolContext, start: dt.date, end: dt.date, limit: int, rank_by: str) -> list[dict]:
    a, b = _bounds(ctx, start, end)
    rows = ctx.store.execute(
        select(Product.sku, Product.name, OrderItem.quantity, OrderItem.unit_price)
        .select_from(OrderItem).join(Order, OrderItem.order_id == Order.id)
        .join(Variant, OrderItem.variant_id == Variant.id).join(Product, Variant.product_id == Product.id)
        .where(Order.status != "cancelled", Order.created_at >= a, Order.created_at < b)
    ).all()
    agg: dict[str, dict] = {}
    for sku, name, qty, price in rows:
        e = agg.setdefault(sku, {"sku": sku, "name": name, "units": 0, "revenue": Decimal(0)})
        e["units"] += qty
        e["revenue"] += price * qty
    key = (lambda e: (-e["units"], -e["revenue"], e["sku"])) if rank_by == "units" \
        else (lambda e: (-e["revenue"], -e["units"], e["sku"]))
    ranked = sorted(agg.values(), key=key)[:limit]
    return [{"rank": i + 1, "sku": e["sku"], "name": e["name"], "units": e["units"], "revenue": money(e["revenue"])}
            for i, e in enumerate(ranked)]


@tool("sales_summary",
      "Totals for a date range: number of orders, revenue (PKR), units sold, average order value, discounts, "
      "cancelled orders. Cancelled orders are excluded from revenue. Exact figures from the database.",
      RangeArgs, {"analytics"}, ADMIN_ONLY)
def sales_summary(ctx: ToolContext, a: RangeArgs) -> dict:
    return _public(_summary(ctx, a.start_date, a.end_date))


class BestSellersArgs(RangeArgs):
    limit: int = Field(5, ge=1, le=20)
    rank_by: Literal["units", "revenue"] = "units"


@tool("best_selling_products",
      "Rank products by units sold or revenue within a date range (cancelled orders excluded).",
      BestSellersArgs, {"analytics"}, ADMIN_ONLY)
def best_selling_products(ctx: ToolContext, a: BestSellersArgs) -> dict:
    return {"start_date": a.start_date.isoformat(), "end_date": a.end_date.isoformat(), "rank_by": a.rank_by,
            "currency": ctx.settings.currency,
            "products": _best_sellers(ctx, a.start_date, a.end_date, a.limit, a.rank_by)}


class TrendArgs(RangeArgs):
    granularity: Literal["day", "week", "month"] = "day"


@tool("sales_trend",
      "Orders and revenue per day, week (Mon-Sun) or month across a date range, with empty periods included as zero.",
      TrendArgs, {"analytics"}, ADMIN_ONLY)
def sales_trend(ctx: ToolContext, a: TrendArgs) -> dict:
    tz = business_tz(ctx.settings)
    lo, hi = _bounds(ctx, a.start_date, a.end_date)

    def bucket(d: dt.date) -> str:
        if a.granularity == "day":
            return d.isoformat()
        if a.granularity == "week":
            return (d - dt.timedelta(days=d.weekday())).isoformat()
        return d.strftime("%Y-%m")

    buckets: dict[str, dict] = {}
    d = a.start_date
    while d <= a.end_date:                     # zero-fill so charts show quiet periods honestly
        buckets.setdefault(bucket(d), {"period": bucket(d), "orders": 0, "revenue": Decimal(0)})
        d += dt.timedelta(days=1)
    for created, total in ctx.store.execute(select(Order.created_at, Order.total).where(
            Order.status != "cancelled", Order.created_at >= lo, Order.created_at < hi)).all():
        b = buckets[bucket(to_local_date(created, tz))]
        b["orders"] += 1
        b["revenue"] += total
    points = [{"period": b["period"], "orders": b["orders"], "revenue": money(b["revenue"])}
              for b in sorted(buckets.values(), key=lambda x: x["period"])]
    return {"granularity": a.granularity, "currency": ctx.settings.currency, "points": points}


class PeriodArgs(StrictModel):
    period: Literal["daily", "weekly", "monthly"]
    anchor_date: dt.date | None = Field(None, description="Any day inside the wanted period. Default: today.")


@tool("period_report",
      "Daily, weekly (Mon-Sun) or monthly (calendar month) sales report containing totals, the top 5 products, and "
      "the % change versus the previous period. Use this for 'daily/weekly/monthly summary' requests.",
      PeriodArgs, {"analytics"}, ADMIN_ONLY)
def period_report(ctx: ToolContext, a: PeriodArgs) -> dict:
    today = ctx.now.astimezone(business_tz(ctx.settings)).date()
    anchor = a.anchor_date or today
    if a.period == "daily":
        s, e = anchor, anchor
        ps = pe = anchor - dt.timedelta(days=1)
    elif a.period == "weekly":
        s = anchor - dt.timedelta(days=anchor.weekday()); e = s + dt.timedelta(days=6)
        ps, pe = s - dt.timedelta(days=7), s - dt.timedelta(days=1)
    else:
        s = anchor.replace(day=1); e = (s + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
        pe = s - dt.timedelta(days=1); ps = pe.replace(day=1)
    cur, prev = _summary(ctx, s, e), _summary(ctx, ps, pe)
    return {
        "period": a.period, "start_date": s.isoformat(), "end_date": e.isoformat(),
        "summary": _public(cur), "previous_period": _public(prev),
        "change_vs_previous": {
            "revenue_percent": _pct_change(cur["_revenue_raw"], prev["_revenue_raw"]),
            "orders_percent": _pct_change(Decimal(cur["orders"]), Decimal(prev["orders"])),
        },
        "top_products": _best_sellers(ctx, s, e, 5, "units"),
    }


class LowStockArgs(StrictModel):
    threshold: int | None = Field(None, ge=0, le=200, description="Flag variants with stock <= this. Default from settings.")
    limit: int = Field(40, ge=1, le=100)


@tool("low_stock_report",
      "List product variants (product/color/size) whose stock is at or below a threshold, lowest first, plus counts.",
      LowStockArgs, {"analytics"}, STAFF)
def low_stock_report(ctx: ToolContext, a: LowStockArgs) -> dict:
    thr = a.threshold if a.threshold is not None else ctx.settings.low_stock_threshold
    q = (select(Product.sku, Product.name, Variant.variant_sku, Variant.stock, Variant.color_id, Variant.size_id)
         .join(Variant, Variant.product_id == Product.id).where(Product.is_active.is_(True), Variant.stock <= thr))
    rows = ctx.store.execute(q.order_by(Variant.stock, Product.sku)).all()
    from ..models_store import Color, Size
    colors = {c.id: c.name for c in ctx.store.scalars(select(Color))}
    sizes = {s.id: s.label for s in ctx.store.scalars(select(Size))}
    items = [{"sku": r.sku, "name": r.name, "color": colors[r.color_id], "size": sizes[r.size_id], "stock": r.stock}
             for r in rows[: a.limit]]
    return {"threshold": thr, "variants_flagged": len(rows), "out_of_stock_variants": sum(1 for r in rows if r.stock == 0),
            "products_affected": len({r.sku for r in rows}), "shown": len(items), "items": items}
