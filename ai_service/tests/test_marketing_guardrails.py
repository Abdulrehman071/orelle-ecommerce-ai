"""Marketing copy must never contain prices/discounts the store has not confirmed."""
import pytest

from app.guardrails import check_claims, collect_facts
from app.tools import execute
from conftest import NOW


def facts(ctx, skus):
    return collect_facts(ctx.store, skus, NOW)


def test_real_price_and_real_sale_discount_pass(ctx_for):
    with ctx_for("admin") as ctx:
        f = facts(ctx, ["OF-1002"])
    assert check_claims("Floral Sundress now PKR 4,000 (was PKR 5,000) - that's 20% off!", f) == []


def test_invented_price_and_discount_are_flagged(ctx_for):
    with ctx_for("admin") as ctx:
        f = facts(ctx, ["OF-1001"])
    w = check_claims("Only Rs. 799 today! Enjoy 50% off, buy one get one free.", f)
    assert any("799" in x for x in w) and any("50%" in x for x in w) and any("buy one get one" in x for x in w)


def test_active_coupon_is_allowed_but_expired_coupon_is_not(ctx_for):
    with ctx_for("admin") as ctx:
        f = facts(ctx, ["OF-1001"])
    assert check_claims("Use code ACTIVE10 for 10% off orders over PKR 2,000.", f) == []
    assert any("20%" in x for x in check_claims("Use EXPIRED20 for 20% off", f))     # EXPIRED20 ended 9 Oct


def test_shipping_rule_numbers_are_allowed(ctx_for):
    with ctx_for("admin") as ctx:
        f = facts(ctx, [])
    assert check_claims("Free shipping above PKR 5,000.", f) == []


def test_unknown_sku_is_flagged(ctx_for):
    with ctx_for("admin") as ctx:
        w = check_claims("hello", facts(ctx, ["OF-0000"]))
    assert any("OF-0000" in x for x in w)


def test_get_confirmed_offers_lists_only_valid_coupons(ctx_for):
    with ctx_for("admin") as ctx:
        d = execute(ctx, "marketing", "get_confirmed_offers", {})["data"]
    assert [c["code"] for c in d["active_coupons"]] == ["ACTIVE10"]
    assert [p["sku"] for p in d["products_on_sale"]] == ["OF-1002"]
    assert "5000" in d["free_shipping_rule"]


def test_save_draft_stores_draft_with_warnings_and_never_publishes(ctx_for, db):
    with ctx_for("admin") as ctx:
        r = execute(ctx, "marketing", "save_draft", dict(kind="instagram_caption", title="Tee push",
                    body="Our tee, now only PKR 499!", product_skus=["OF-1001"]))
        ctx.agent.commit()
    assert r["ok"] and r["data"]["draft"]["status"] == "draft" and len(r["data"]["fact_check_warnings"]) == 1


def test_marketing_tools_are_staff_only(ctx_for):
    with ctx_for("alice") as ctx:
        for tool, args in [("get_confirmed_offers", {}), ("save_draft", dict(kind="facebook_post", title="x" * 3, body="hello there"))]:
            assert "not authorized" in execute(ctx, "marketing", tool, args)["error"]
