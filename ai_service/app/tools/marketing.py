"""Marketing tools: what offers are REAL, and saving drafts (never publishing)."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from sqlalchemy import select

from ..drafts import draft_view
from ..guardrails import check_claims, collect_facts
from ..models_agent import Draft
from ..models_store import Coupon, Product
from ..policies import load_policies
from .base import STAFF, StrictModel, ToolContext, money, tool


class NoArgs(StrictModel):
    pass


@tool("get_confirmed_offers",
      "The ONLY source of truth for promotions: currently valid coupon codes, products currently on sale, and the "
      "free-shipping rule. If something is not listed here, it is NOT an offer and must not be promoted.",
      NoArgs, {"marketing"}, STAFF)
def get_confirmed_offers(ctx: ToolContext, a: NoArgs) -> dict:
    naive_now = ctx.now.replace(tzinfo=None)
    coupons = ctx.store.scalars(select(Coupon).where(Coupon.is_active.is_(True), Coupon.start_date <= naive_now,
                                                      Coupon.expiry_date >= naive_now)).all()
    on_sale = ctx.store.scalars(select(Product).where(Product.is_active.is_(True), Product.sale_price.is_not(None))
                                .order_by(Product.name).limit(20)).unique().all()
    rules = load_policies()["shipping_rules"]
    return {
        "currency": ctx.settings.currency,
        "active_coupons": [{"code": c.code, "type": c.discount_type, "value": money(c.value),
                            "min_order_amount": money(c.min_order_amount),
                            "max_discount_amount": money(c.max_discount_amount),
                            "valid_until": c.expiry_date.date().isoformat()} for c in coupons],
        "products_on_sale": [{"sku": p.sku, "name": p.name, "price": money(p.price), "sale_price": money(p.sale_price),
                              "discount_percent": p.discount_percent} for p in on_sale],
        "free_shipping_rule": f"Free standard shipping on orders of {rules['free_shipping_threshold']} {ctx.settings.currency} or more.",
    }


DraftKind = Literal["product_description", "facebook_post", "instagram_caption", "promo_message",
                    "campaign_idea", "content_calendar"]


class SaveDraftArgs(StrictModel):
    kind: DraftKind
    title: str = Field(..., min_length=2, max_length=120)
    body: str = Field(..., min_length=5, max_length=4000, description="Plain text, ready for a human to edit.")
    product_skus: list[str] = Field(default_factory=list, max_length=10,
                                    description="SKUs of the real products this draft mentions (used for fact checking).")


@tool("save_draft",
      "Save a finished marketing piece as an editable DRAFT for human review. Nothing is published. "
      "The system fact-checks prices/discounts in the text against store data and returns warnings.",
      SaveDraftArgs, {"marketing"}, STAFF)
def save_draft(ctx: ToolContext, a: SaveDraftArgs) -> dict:
    facts = collect_facts(ctx.store, a.product_skus, ctx.now)
    warnings = check_claims(f"{a.title}\n{a.body}", facts)
    d = Draft(business_id=ctx.business_id, task_id=ctx.task_id, kind=a.kind, title=a.title, body=a.body,
              status="draft", warnings=warnings, product_skus=a.product_skus, created_by=ctx.principal.user_id)
    ctx.agent.add(d)
    ctx.agent.flush()
    return {"saved": True, "draft": draft_view(d), "fact_check_warnings": warnings}
