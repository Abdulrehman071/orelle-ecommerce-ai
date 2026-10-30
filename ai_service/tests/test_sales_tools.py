"""Sales numbers must equal what the database says. Expected values come from independent raw SQL, not from our tools."""
import sqlite3

import pytest

from app.tools import execute
from conftest import NOW

# October 2026 in Pakistan time = [2026-09-30 19:00 UTC, 2026-10-31 19:00 UTC)
OCT = ("2026-09-30 19:00:00", "2026-10-31 19:00:00")


def run(ctx, tool, **args):
    return execute(ctx, "analytics", tool, args)


def raw(store_path, sql, *params):
    con = sqlite3.connect(store_path)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def test_monthly_totals_match_raw_sql(ctx_for, store_path):
    revenue, orders = raw(store_path, "SELECT SUM(total), COUNT(*) FROM orders_order WHERE status!='cancelled' AND created_at>=? AND created_at<?", *OCT)[0]
    units = raw(store_path, "SELECT SUM(i.quantity) FROM orders_orderitem i JOIN orders_order o ON o.id=i.order_id WHERE o.status!='cancelled' AND o.created_at>=? AND o.created_at<?", *OCT)[0][0]
    with ctx_for("admin") as ctx:
        r = run(ctx, "sales_summary", start_date="2026-10-01", end_date="2026-10-31")
    assert r["ok"]
    d = r["data"]
    assert d["orders"] == orders == 3
    assert d["revenue"] == float(revenue) == 14600
    assert d["units_sold"] == units == 6
    assert d["discounts_given"] == 900
    assert d["average_order_value"] == pytest.approx(14600 / 3, abs=0.01)
    assert d["cancelled_orders"] == 1                      # reported, but excluded from revenue
    assert "_revenue_raw" not in d


def test_cancelled_orders_are_excluded_from_best_sellers(ctx_for):
    with ctx_for("admin") as ctx:
        r = run(ctx, "best_selling_products", start_date="2026-10-01", end_date="2026-10-31", limit=5)
    prods = r["data"]["products"]
    # OF-1001: 2+1 = 3 units (the cancelled 5-unit order is ignored). OF-1002: 1+2 = 3 units.
    assert {p["sku"]: p["units"] for p in prods} == {"OF-1001": 3, "OF-1002": 3}
    assert prods[0]["sku"] == "OF-1002" and prods[0]["rank"] == 1   # tie on units -> higher revenue wins (12000 vs 3000)
    assert prods[0]["revenue"] == 12000


def test_rank_by_revenue(ctx_for):
    with ctx_for("admin") as ctx:
        r = run(ctx, "best_selling_products", start_date="2026-10-01", end_date="2026-10-31", rank_by="revenue", limit=1)
    assert r["data"]["products"][0]["sku"] == "OF-1002"


def test_business_timezone_day_boundary(ctx_for):
    """ORD-10004 is 20:00 UTC on Oct 20 = 01:00 on Oct 21 in Pakistan, so it belongs to Oct 21."""
    with ctx_for("admin") as ctx:
        d20 = run(ctx, "sales_summary", start_date="2026-10-20", end_date="2026-10-20")["data"]
        d21 = run(ctx, "sales_summary", start_date="2026-10-21", end_date="2026-10-21")["data"]
    assert d20["orders"] == 0 and d21["orders"] == 1 and d21["revenue"] == 8100


def test_period_report_monthly_with_comparison(ctx_for):
    with ctx_for("admin") as ctx:
        r = run(ctx, "period_report", period="monthly", anchor_date="2026-10-15")["data"]
    assert (r["start_date"], r["end_date"]) == ("2026-10-01", "2026-10-31")
    assert r["summary"]["revenue"] == 14600
    assert r["previous_period"]["revenue"] == 1250                       # September: ORD-10005
    assert r["change_vs_previous"]["revenue_percent"] == 1068.0          # (14600-1250)/1250*100
    assert [p["sku"] for p in r["top_products"]][0] == "OF-1002"


def test_period_report_weekly_monday_to_sunday_and_no_previous_data(ctx_for):
    with ctx_for("admin") as ctx:
        r = run(ctx, "period_report", period="weekly", anchor_date="2026-10-21")["data"]  # a Wednesday
    assert (r["start_date"], r["end_date"]) == ("2026-10-19", "2026-10-25")
    assert r["summary"]["orders"] == 1
    assert r["previous_period"]["orders"] == 0                            # prev week only has a cancelled order
    assert r["change_vs_previous"]["revenue_percent"] is None             # no divide-by-zero, no invented %


def test_period_report_defaults_to_today_in_business_timezone(ctx_for):
    with ctx_for("admin") as ctx:
        r = run(ctx, "period_report", period="daily")["data"]
    assert r["start_date"] == r["end_date"] == "2026-10-28"               # NOW = 2026-10-28 12:00 UTC


def test_sales_trend_zero_fills_quiet_days(ctx_for):
    with ctx_for("admin") as ctx:
        pts = run(ctx, "sales_trend", start_date="2026-10-19", end_date="2026-10-23", granularity="day")["data"]["points"]
    assert [p["period"] for p in pts] == ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
    assert [p["orders"] for p in pts] == [0, 0, 1, 0, 0] and pts[2]["revenue"] == 8100


def test_sales_trend_monthly_buckets(ctx_for):
    with ctx_for("admin") as ctx:
        pts = run(ctx, "sales_trend", start_date="2026-09-01", end_date="2026-10-31", granularity="month")["data"]["points"]
    assert pts == [{"period": "2026-09", "orders": 1, "revenue": 1250}, {"period": "2026-10", "orders": 3, "revenue": 14600}]


def test_empty_period_returns_zeros_not_inventions(ctx_for):
    with ctx_for("admin") as ctx:
        d = run(ctx, "sales_summary", start_date="2026-01-01", end_date="2026-01-31")["data"]
    assert d["orders"] == 0 and d["revenue"] == 0 and d["average_order_value"] is None


def test_low_stock_report_default_and_custom_threshold(ctx_for):
    with ctx_for("staff") as ctx:
        d = run(ctx, "low_stock_report")["data"]                          # default threshold = 5
        d0 = run(ctx, "low_stock_report", threshold=0)["data"]
    assert d["threshold"] == 5 and d["variants_flagged"] == 5 and d["out_of_stock_variants"] == 3
    assert d["products_affected"] == 3                                    # inactive product OF-1003 is excluded
    assert [i["stock"] for i in d["items"]] == [0, 0, 0, 3, 5]            # lowest first
    assert d0["variants_flagged"] == 3 and all(i["stock"] == 0 for i in d0["items"])


@pytest.mark.parametrize("args", [
    {"start_date": "2026-10-31", "end_date": "2026-10-01"},               # end before start
    {"start_date": "2024-01-01", "end_date": "2026-10-01"},               # > 366 days
    {"start_date": "not-a-date", "end_date": "2026-10-01"},
    {"start_date": "2026-10-01"},                                          # missing field
    {"start_date": "2026-10-01", "end_date": "2026-10-02", "sql": "DROP TABLE x"},   # unexpected extra argument
])
def test_invalid_inputs_are_rejected_with_a_clean_error(ctx_for, args):
    with ctx_for("admin") as ctx:
        r = run(ctx, "sales_summary", **args)
    assert r["ok"] is False and "Invalid input" in r["error"]


def test_staff_cannot_read_revenue_but_can_see_stock(ctx_for):
    with ctx_for("staff") as ctx:
        denied = run(ctx, "sales_summary", start_date="2026-10-01", end_date="2026-10-31")
        allowed = run(ctx, "low_stock_report")
        recorded = [(r.tool, r.status) for r in ctx.records]
    assert denied == {"ok": False, "error": "You are not authorized to use this tool."}
    assert allowed["ok"]
    assert recorded == [("sales_summary", "denied"), ("low_stock_report", "ok")]


@pytest.mark.parametrize("who", ["anonymous", "alice"])
def test_customers_and_visitors_cannot_use_any_analytics_tool(ctx_for, who):
    with ctx_for(who) as ctx:
        for tool in ("sales_summary", "best_selling_products", "sales_trend", "period_report", "low_stock_report"):
            r = execute(ctx, "analytics", tool, {})
            assert r["ok"] is False and "not authorized" in r["error"]


def test_store_database_cannot_be_written(db):
    from sqlalchemy import text
    from app.db import StoreReadOnlyError
    with db.store_session() as s:
        with pytest.raises(StoreReadOnlyError):
            s.execute(text("UPDATE catalog_productvariant SET stock = 999"))
        with pytest.raises(StoreReadOnlyError):
            s.execute(text("DELETE FROM orders_order"))
