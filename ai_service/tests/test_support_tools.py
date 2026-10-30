import pytest

from app.tools import execute


def run(ctx, tool, agent="support", **args):
    return execute(ctx, agent, tool, args)


# ------------------------------------------------------------------ products & stock
def test_search_finds_real_products_with_real_prices(ctx_for):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "search_products", query="tee")["data"]
    assert r["count"] == 1
    p = r["products"][0]
    assert (p["sku"], p["price"], p["sale_price"], p["current_price"], p["currency"]) == ("OF-1001", 1000, None, 1000, "PKR")
    assert p["availability"] == "in_stock" and p["colors_in_stock"] == ["Black"]     # Navy M has 0 stock


def test_search_sale_price_and_discount_percent(ctx_for):
    with ctx_for("anonymous") as ctx:
        p = run(ctx, "search_products", query="sundress")["data"]["products"][0]
    assert (p["price"], p["sale_price"], p["current_price"], p["discount_percent"]) == (5000, 4000, 4000, 20)


def test_search_plural_and_case_insensitive(ctx_for):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "search_products", query="T-SHIRTS")["data"]["products"]   # category-name match, plural + upper-case
        assert {p["sku"] for p in r} == {"OF-1001", "OF-1004"}                     # both live in the T-Shirts category
        assert run(ctx, "search_products", query="dresses", department="women")["data"]["count"] == 1


def test_inactive_products_are_hidden_from_customers(ctx_for):
    with ctx_for("anonymous") as ctx:
        assert run(ctx, "search_products", query="hidden")["data"]["count"] == 0
        r = run(ctx, "get_product_details", sku="OF-1003")
    assert r["ok"] is False and "No product found" in r["error"]


def test_staff_can_see_inactive_products(ctx_for):
    with ctx_for("staff") as ctx:
        r = run(ctx, "get_product_details", sku="OF-1003")
    assert r["ok"] and r["data"]["is_active"] is False


def test_filters_color_size_price_and_in_stock(ctx_for):
    with ctx_for("anonymous") as ctx:
        navy = run(ctx, "search_products", color="Navy")["data"]["products"]
        navy_in_stock = run(ctx, "search_products", color="Navy", in_stock_only=True)["data"]["products"]
        cheap = run(ctx, "search_products", max_price=1500)["data"]["products"]
        size_l = run(ctx, "search_products", size="L", in_stock_only=True)["data"]["products"]
    assert {p["sku"] for p in navy} == {"OF-1001", "OF-1004"}
    assert navy_in_stock == []                                   # every Navy variant is at 0 stock
    assert [p["sku"] for p in cheap] == ["OF-1001"]
    assert [p["sku"] for p in size_l] == ["OF-1002"]


def test_unavailable_product_reports_out_of_stock(ctx_for):
    with ctx_for("anonymous") as ctx:
        p = run(ctx, "get_product_details", sku="OF-1004")["data"]
    assert p["availability"] == "out_of_stock" and not any(v["in_stock"] for v in p["variants"])


def test_unknown_sku_is_a_clean_error_not_a_guess(ctx_for):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "get_product_details", sku="OF-9999")
    assert r == {"ok": False, "error": "No product found with SKU 'OF-9999'."}


def test_customers_see_availability_but_not_exact_stock_staff_do(ctx_for):
    with ctx_for("anonymous") as ctx:
        v = run(ctx, "get_product_details", sku="OF-1001")["data"]
    assert all("stock" not in x for x in v["variants"]) and "total_stock" not in v
    assert {"color": "Black", "size": "M", "in_stock": True, "units_left": 3} in v["variants"]   # low-stock hint only
    with ctx_for("staff") as ctx:
        v = run(ctx, "get_product_details", sku="OF-1001")["data"]
    assert v["total_stock"] == 13 and {"color": "Black", "size": "S", "in_stock": True, "stock": 10} in v["variants"]


def test_search_input_is_not_sql_injectable(ctx_for):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "search_products", query="'; DROP TABLE catalog_product; --")
        assert r["ok"] and r["data"]["count"] == 0
        assert run(ctx, "search_products", query="100%")["data"]["count"] == 0      # % is escaped, not a wildcard
        assert run(ctx, "search_products")["data"]["count"] == 4 - 1                # table is intact (3 active products)


def test_bad_tool_arguments_are_rejected(ctx_for):
    with ctx_for("anonymous") as ctx:
        assert "Invalid input" in run(ctx, "search_products", limit=500)["error"]
        assert "Invalid input" in run(ctx, "search_products", department="kids")["error"]
        assert "Invalid input" in run(ctx, "get_product_details")["error"]
        assert "Unknown tool" in run(ctx, "delete_everything")["error"]


# ------------------------------------------------------------------ policies
def test_policies_come_from_the_store_policy_file(ctx_for):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "get_store_policies", topic="returns")["data"]
        s = run(ctx, "get_store_policies", topic="shipping")["data"]
    assert "14 days" in r["policies"]["returns"]
    assert s["shipping_rules"] == {"standard_fee": 250, "express_fee": 600, "free_shipping_threshold": 5000,
                                   "standard_days": "5-7", "express_days": "2-4"}


# ------------------------------------------------------------------ order privacy
def test_guest_needs_matching_email(ctx_for):
    with ctx_for("anonymous") as ctx:
        ok = run(ctx, "lookup_order", order_number="ord-10002", email="BOB@example.com")      # case-insensitive
        wrong = run(ctx, "lookup_order", order_number="ORD-10002", email="alice@example.com")
        no_email = run(ctx, "lookup_order", order_number="ORD-10002")
        missing = run(ctx, "lookup_order", order_number="ORD-99999", email="bob@example.com")
    assert ok["ok"] and ok["data"]["status"] == "shipped" and ok["data"]["shipment"]["tracking_number"] == "LEO9"
    # 'not yours' and 'does not exist' must be indistinguishable (no order-number probing)
    assert wrong == no_email == missing == {"ok": False, "error": "No order found for that order number and email."}


def test_logged_in_customer_sees_only_own_orders(ctx_for):
    with ctx_for("alice") as ctx:
        own = run(ctx, "lookup_order", order_number="ORD-10001")
        bobs = run(ctx, "lookup_order", order_number="ORD-10002")
        bobs_with_guess = run(ctx, "lookup_order", order_number="ORD-10002", email="alice@example.com")
    assert own["ok"] and own["data"]["total"] == 2250
    assert bobs["ok"] is False and bobs_with_guess["ok"] is False


def test_order_lookup_never_returns_address_phone_or_email(ctx_for):
    with ctx_for("alice") as ctx:
        d = run(ctx, "lookup_order", order_number="ORD-10001")["data"]
    blob = str(d).lower()
    for secret in ("alice@example.com", "address", "phone", "postal"):
        assert secret not in blob


def test_staff_can_look_up_any_order(ctx_for):
    with ctx_for("staff") as ctx:
        assert run(ctx, "lookup_order", order_number="ORD-10002")["ok"]


# ------------------------------------------------------------------ escalation
def test_escalation_creates_a_pending_review_item_and_sends_nothing(ctx_for, db):
    with ctx_for("anonymous") as ctx:
        r = run(ctx, "escalate_to_human", reason="Refund request", customer_message="I want my money back for ORD-10001",
                suggested_reply="Sorry about that - a team member will contact you.", contact="a@b.com")
        ctx.agent.commit()
    d = r["data"]["draft"]
    assert r["data"]["escalated"] and d["status"] == "pending_review" and d["kind"] == "support_escalation"
    assert d["meta"]["contact"] == "a@b.com" and "DRAFT - not sent" in d["body"]
