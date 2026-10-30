"""Marketing guard-rail: every price, discount percentage and offer in a draft must be backed by real store data.

This is a deterministic check (regular expressions + database facts), NOT another AI call, so it cannot be
talked out of its job. It is a safety net, not a guarantee: a human still reviews and approves every draft.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models_store import Coupon, Product
from .policies import load_policies

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MONEY = re.compile(r"(?:PKR|Rs\.?|₨)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:PKR|rupees)", re.I)
_RISKY_PHRASES = ("buy one get one", "bogo", "buy 1 get 1", "free gift", "giveaway", "guaranteed", "lifetime warranty")


def _d(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"))


@dataclass
class Facts:
    amounts: set[Decimal] = field(default_factory=set)
    percents: set[Decimal] = field(default_factory=set)
    unknown_skus: list[str] = field(default_factory=list)


def collect_facts(store: Session, skus: list[str], now_utc: dt.datetime) -> Facts:
    facts = Facts()
    for sku in skus:
        p = store.scalars(select(Product).where(func.lower(Product.sku) == sku.lower())).first()
        if p is None:
            facts.unknown_skus.append(sku)
            continue
        facts.amounts.add(_d(p.price))
        if p.sale_price:
            facts.amounts.add(_d(p.sale_price))
            facts.percents.add(_d(p.discount_percent))
    naive_now = now_utc.replace(tzinfo=None)
    for c in store.scalars(select(Coupon).where(Coupon.is_active.is_(True), Coupon.start_date <= naive_now,
                                                 Coupon.expiry_date >= naive_now)):
        if c.discount_type == "percentage":
            facts.percents.add(_d(c.value))
        else:
            facts.amounts.add(_d(c.value))
        facts.amounts.add(_d(c.min_order_amount))
        if c.max_discount_amount:
            facts.amounts.add(_d(c.max_discount_amount))
    rules = load_policies()["shipping_rules"]
    for k in ("standard_fee", "express_fee", "free_shipping_threshold"):
        facts.amounts.add(_d(rules[k]))
    return facts


def check_claims(text: str, facts: Facts) -> list[str]:
    warnings: list[str] = []
    for sku in facts.unknown_skus:
        warnings.append(f"Unknown product SKU '{sku}' - its details could not be verified.")
    for m in _MONEY.finditer(text):
        raw = (m.group(1) or m.group(2)).replace(",", "")
        if _d(raw) not in facts.amounts:
            warnings.append(f"Unverified price/amount '{m.group(0).strip()}' - not found in store data. Check before publishing.")
    for m in _PCT.finditer(text):
        if _d(m.group(1)) not in facts.percents:
            warnings.append(f"Unverified discount '{m.group(0).strip()}' - no active coupon or sale price has this value.")
    low = text.lower()
    for phrase in _RISKY_PHRASES:
        if phrase in low:
            warnings.append(f"Unconfirmed offer/claim wording '{phrase}' - the store has not confirmed this.")
    return warnings
