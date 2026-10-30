"""Product, stock and policy tools (read-only). Used by the Support agent; products also by Marketing."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ..models_store import Category, Color, Product, Size, Variant
from ..policies import load_policies
from .base import ALL_ROLES, STAFF, StrictModel, ToolContext, ToolError, money, tool


def _esc(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _stem(t: str) -> str:
    t = t.lower()
    return t[:-1] if len(t) > 3 and t.endswith("s") else t


def _availability(total: int, threshold: int) -> str:
    return "out_of_stock" if total <= 0 else ("low_stock" if total <= threshold else "in_stock")


def product_summary(p: Product, ctx: ToolContext, detail: bool = False) -> dict:
    thr = ctx.settings.low_stock_threshold
    total = sum(v.stock for v in p.variants)
    in_stock_colors = sorted({v.color.name for v in p.variants if v.stock > 0})
    out = {
        "sku": p.sku, "name": p.name, "category": p.category.name, "department": p.category.department,
        "price": money(p.price), "sale_price": money(p.sale_price), "current_price": money(p.current_price),
        "discount_percent": p.discount_percent, "currency": ctx.settings.currency, "fit": p.fit,
        "colors_in_stock": in_stock_colors, "availability": _availability(total, thr),
        "is_new_arrival": p.is_new_arrival,
    }
    if detail:
        sizes_order = {v.size.label: v.size.order for v in p.variants}
        out.update({"description": p.description, "material": p.material, "care_instructions": p.care_instructions})
        variants = []
        for v in sorted(p.variants, key=lambda v: (v.color.name, v.size.order)):
            item = {"color": v.color.name, "size": v.size.label, "in_stock": v.stock > 0}
            if ctx.principal.is_staff:
                item["stock"] = v.stock  # exact quantities are for staff only
            elif 0 < v.stock <= thr:
                item["units_left"] = v.stock
            variants.append(item)
        out["variants"] = variants
        out["sizes"] = sorted(sizes_order, key=sizes_order.get)
        if ctx.principal.is_staff:
            out["total_stock"] = total
            out["is_active"] = p.is_active
    return out


class SearchProductsArgs(StrictModel):
    query: str | None = Field(None, max_length=100, description="Short keywords, e.g. 'polo' or 'cargo trouser'.")
    department: Literal["men", "women", "juniors"] | None = None
    color: str | None = Field(None, max_length=30)
    size: str | None = Field(None, max_length=10, description="e.g. S, M, L, XL")
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    in_stock_only: bool = False
    limit: int = Field(8, ge=1, le=15)


@tool("search_products",
      "Search the real product catalogue by keywords, department, color, size, price range and availability. "
      "Returns prices (PKR) and stock availability from the live store database.",
      SearchProductsArgs, {"support", "marketing"}, ALL_ROLES)
def search_products(ctx: ToolContext, a: SearchProductsArgs) -> dict:
    price_col = func.coalesce(Product.sale_price, Product.price)
    stmt = (select(Product).join(Category, Product.category_id == Category.id)
            .where(Product.is_active.is_(True)).options(selectinload(Product.variants)))
    for term in (a.query or "").split()[:6]:
        pat = _esc(_stem(term))
        stmt = stmt.where(or_(Product.name.ilike(pat, escape="\\"), Product.sku.ilike(pat, escape="\\"),
                              Product.description.ilike(pat, escape="\\"), Category.name.ilike(pat, escape="\\")))
    if a.department:
        stmt = stmt.where(Category.department == a.department)
    if a.min_price is not None:
        stmt = stmt.where(price_col >= a.min_price)
    if a.max_price is not None:
        stmt = stmt.where(price_col <= a.max_price)
    if a.color or a.size or a.in_stock_only:
        vq = (select(Variant.id).join(Color, Variant.color_id == Color.id).join(Size, Variant.size_id == Size.id)
              .where(Variant.product_id == Product.id))
        if a.color:
            vq = vq.where(func.lower(Color.name) == a.color.lower())
        if a.size:
            vq = vq.where(func.lower(Size.label) == a.size.lower())
        if a.in_stock_only:
            vq = vq.where(Variant.stock > 0)
        stmt = stmt.where(vq.exists())
    rows = ctx.store.scalars(stmt.order_by(Product.name, Product.sku).limit(a.limit)).unique().all()
    return {"count": len(rows), "products": [product_summary(p, ctx) for p in rows]}


class ProductDetailsArgs(StrictModel):
    sku: str = Field(..., min_length=2, max_length=50, description="Product SKU such as OF-1016")


@tool("get_product_details",
      "Get full details for ONE product by SKU: description, material, care, price, and availability per color/size.",
      ProductDetailsArgs, {"support", "marketing"}, ALL_ROLES)
def get_product_details(ctx: ToolContext, a: ProductDetailsArgs) -> dict:
    stmt = select(Product).where(func.lower(Product.sku) == a.sku.lower()).options(selectinload(Product.variants))
    if not ctx.principal.is_staff:
        stmt = stmt.where(Product.is_active.is_(True))
    p = ctx.store.scalars(stmt).unique().first()
    if p is None:
        raise ToolError(f"No product found with SKU '{a.sku}'.")
    return product_summary(p, ctx, detail=True)


class PolicyArgs(StrictModel):
    topic: Literal["shipping", "returns", "exchanges", "payment", "contact", "size_guide", "order_tracking", "all"] = "all"


@tool("get_store_policies",
      "Get the store's official policy text (shipping, returns, exchanges, payment, contact, size guide). "
      "Always use this for policy questions; never answer policy questions from memory.",
      PolicyArgs, {"support", "marketing"}, ALL_ROLES)
def get_store_policies(ctx: ToolContext, a: PolicyArgs) -> dict:
    pol = load_policies()
    topics = pol["topics"] if a.topic == "all" else {a.topic: pol["topics"][a.topic]}
    out = {"currency": pol["store"]["currency"], "policies": topics}
    if a.topic in ("all", "shipping"):
        out["shipping_rules"] = pol["shipping_rules"]
    return out
