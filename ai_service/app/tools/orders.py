"""Customer-facing order lookup (privacy-checked) and escalation to a human."""
from __future__ import annotations

from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..drafts import draft_view
from ..models_agent import Draft
from ..models_store import Order
from ..timeutil import business_tz, to_local_date
from .base import ALL_ROLES, StrictModel, ToolContext, ToolError, money, tool

NOT_FOUND = "No order found for that order number and email."  # same message for 'missing' and 'not yours'


class LookupOrderArgs(StrictModel):
    order_number: str = Field(..., min_length=3, max_length=20, description="e.g. ORD-12345")
    email: str | None = Field(None, max_length=254, description="The email used at checkout.")


@tool("lookup_order",
      "Look up the status of ONE order. Customers must provide the order number AND the email used at checkout "
      "(or be logged in as the owner). Never reveals other customers' orders.",
      LookupOrderArgs, {"support"}, ALL_ROLES)
def lookup_order(ctx: ToolContext, a: LookupOrderArgs) -> dict:
    o = ctx.store.scalars(
        select(Order).where(func.upper(Order.order_number) == a.order_number.upper())
        .options(selectinload(Order.items), selectinload(Order.shipment))
    ).first()
    p = ctx.principal
    allowed = False
    if o is not None:
        if p.is_staff:
            allowed = True
        elif p.user_id and o.user_id is not None and o.user_id.hex == p.user_id:
            allowed = True
        elif a.email and a.email.strip().lower() == o.email.lower():
            allowed = True
    if not allowed:
        raise ToolError(NOT_FOUND)
    sh = o.shipment
    return {
        "order_number": o.order_number, "status": o.status,
        "placed_on": to_local_date(o.created_at, business_tz(ctx.settings)).isoformat(),
        "delivery_method": o.delivery_method, "payment_method": o.payment_method,
        "items": [{"product": i.product_name, "size": i.size_label, "color": i.color_name,
                   "quantity": i.quantity, "unit_price": money(i.unit_price)} for i in o.items],
        "subtotal": money(o.subtotal), "shipping_fee": money(o.shipping_fee),
        "discount": money(o.discount_amount), "total": money(o.total), "currency": ctx.settings.currency,
        "shipment": None if sh is None else {
            "carrier": sh.carrier or None, "tracking_number": sh.tracking_number or None,
            "estimated_delivery_days": sh.estimated_delivery_days,
            "shipped": sh.shipped_at is not None, "delivered": sh.delivered_at is not None,
        },
    }


class EscalateArgs(StrictModel):
    reason: str = Field(..., min_length=3, max_length=300, description="Why a human must handle this.")
    customer_message: str = Field(..., min_length=1, max_length=1000)
    suggested_reply: str | None = Field(None, max_length=1500, description="Optional draft reply for the staff member.")
    contact: str | None = Field(None, max_length=200, description="Email/phone the customer gave, if any.")


@tool("escalate_to_human",
      "Hand the conversation to a human staff member. Use for refunds, complaints, damaged/wrong items, order changes, "
      "anything sensitive, or anything you cannot answer from store data. Nothing is sent to the customer automatically.",
      EscalateArgs, {"support"}, ALL_ROLES)
def escalate_to_human(ctx: ToolContext, a: EscalateArgs) -> dict:
    body = f"Customer message:\n{a.customer_message}"
    if a.suggested_reply:
        body += f"\n\nSuggested reply (DRAFT - not sent):\n{a.suggested_reply}"
    d = Draft(business_id=ctx.business_id, task_id=ctx.task_id, kind="support_escalation",
              title=a.reason[:200], body=body, status="pending_review", product_skus=[],
              meta={"reason": a.reason, "contact": a.contact or ""}, created_by=ctx.principal.user_id)
    ctx.agent.add(d)
    ctx.agent.flush()
    return {"escalated": True, "reference": d.id[:8], "draft": draft_view(d)}
