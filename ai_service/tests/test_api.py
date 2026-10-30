import sqlite3

from app.db import Database, make_agent_engine, make_store_engine
from app.llm.anthropic_client import UnconfiguredLLM
from conftest import ScriptedLLM, auth, call, make_settings, plan, say


def draft_script(body="Our Floral Sundress, now PKR 4,000. 20% off!", skus=("OF-1002",)):
    return ScriptedLLM(plan(("marketing", "caption")),
                       call("save_draft", kind="instagram_caption", title="Caption", body=body, product_skus=list(skus)),
                       say("Drafted."))


def make_draft(client, who="admin", **kw):
    r = client.post("/chat", json={"message": "write an instagram caption"}, headers=auth(who))
    assert r.status_code == 200, r.text
    return r.json()["structured"]["drafts"][0]


# ------------------------------------------------------------------ auth
def test_health_and_me(make_client):
    c = make_client(ScriptedLLM())
    assert c.get("/health").json() == {"status": "ok", "store_db": True, "llm_configured": True}
    assert c.get("/me").json()["role"] == "anonymous"
    assert c.get("/me", headers=auth("admin")).json() == {"role": "admin", "email": "owner@shop.pk",
                                                          "allowed_agents": ["analytics", "marketing", "support"]}
    assert c.get("/me", headers=auth("alice")).json()["allowed_agents"] == ["support"]


def test_unconfigured_llm_is_reported_honestly(make_client):
    c = make_client(UnconfiguredLLM())
    assert c.get("/health").json()["llm_configured"] is False
    r = c.post("/chat", json={"message": "hi"}).json()
    assert r["status"] == "failed" and "temporarily unavailable" in r["answer"]


def test_bad_tokens_are_rejected_not_downgraded(make_client):
    c = make_client()
    for h in ({"Authorization": "Token nope"}, {"Authorization": "Bearer x"}, {"Authorization": "garbage"},
              auth("inactive")):
        assert c.get("/me", headers=h).status_code == 401
        assert c.post("/chat", json={"message": "hi"}, headers=h).status_code == 401


# ------------------------------------------------------------------ chat
def test_visitor_chat_hides_internal_details(make_client):
    c = make_client(ScriptedLLM(call("search_products", query="tee"), say("PKR 1000, in stock.")))
    j = c.post("/chat", json={"message": "tee price?"}).json()
    assert j["status"] == "completed" and j["answer"] == "PKR 1000, in stock."
    assert not ({"structured", "steps", "agents_used", "plan_source"} & set(j))      # no tool output / trace for customers


def test_staff_chat_includes_trace_and_structured_data(make_client):
    c = make_client(ScriptedLLM(plan(("analytics", "x")), call("low_stock_report"), say("5 variants are low.")))
    j = c.post("/chat", json={"message": "low stock?"}, headers=auth("staff")).json()
    assert j["agents_used"] == ["analytics"] and j["structured"]["tools"]["analytics"]["low_stock_report"][0]["variants_flagged"] == 5
    assert j["steps"][0]["tools"][0]["tool"] == "low_stock_report"


def test_chat_input_validation(make_client):
    c = make_client(ScriptedLLM())
    for body in ({}, {"message": ""}, {"message": "   "}, {"message": "x" * 2001}, {"message": "hi", "history": [{"role": "system", "content": "x"}]},
                 {"message": "hi", "history": [{"role": "user", "content": "x"}] * 13}):
        assert c.post("/chat", json=body).status_code == 422


def test_control_characters_are_stripped(make_client):
    llm = ScriptedLLM(say("ok"))
    make_client(llm).post("/chat", json={"message": "hi\x00\x07 there"})
    assert llm.calls[0]["messages"][0]["content"].startswith("TASK:\nhi there")


def test_rate_limit(make_client):
    c = make_client(UnconfiguredLLM(), rate_limit_per_minute=2)
    codes = [c.post("/chat", json={"message": "hi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_cors_only_for_allowed_origin(make_client):
    c = make_client()
    ok = c.options("/chat", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                     "Access-Control-Request-Headers": "authorization,content-type"})
    bad = c.options("/chat", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


# ------------------------------------------------------------------ staff-only endpoints
def test_history_and_drafts_require_staff(make_client):
    c = make_client()
    for path in ("/history", "/drafts"):
        assert c.get(path).status_code == 403
        assert c.get(path, headers=auth("alice")).status_code == 403
        assert c.get(path, headers=auth("staff")).status_code == 200
    assert c.post("/drafts/abc/approve", json={}, headers=auth("alice")).status_code == 403


def test_activity_history_lists_successes_and_failures(make_client):
    from app.llm.base import LLMUnavailable
    c = make_client(ScriptedLLM(call("search_products", query="tee"), say("ok"), LLMUnavailable("down")))
    c.post("/chat", json={"message": "tee?"})
    c.post("/chat", json={"message": "again"})
    items = c.get("/history", headers=auth("admin")).json()["items"]
    assert [i["status"] for i in items] == ["failed", "completed"] and items[0]["error"]
    assert items[1]["tools"] == [{"agent": "support", "tool": "search_products", "status": "ok", "duration_ms": items[1]["tools"][0]["duration_ms"]}]


# ------------------------------------------------------------------ draft review / approval
def test_edit_rechecks_claims_then_approval_flow(make_client):
    c = make_client(draft_script(body="Floral Sundress, now PKR 999! 20% off!"))
    d = make_draft(c)
    assert any("999" in w for w in d["warnings"])
    # approving with unverified claims needs explicit acknowledgement
    assert c.post(f"/drafts/{d['id']}/approve", json={}, headers=auth("staff")).status_code == 409
    # a human fixes the text -> warnings recomputed server-side
    fixed = c.patch(f"/drafts/{d['id']}", json={"body": "Floral Sundress, now PKR 4,000. 20% off!"}, headers=auth("staff")).json()
    assert fixed["warnings"] == [] and fixed["body"].startswith("Floral")
    ok = c.post(f"/drafts/{d['id']}/approve", json={}, headers=auth("staff")).json()
    assert ok["status"] == "approved"
    # final states are final
    assert c.post(f"/drafts/{d['id']}/approve", json={}, headers=auth("staff")).status_code == 409
    assert c.post(f"/drafts/{d['id']}/reject", json={}, headers=auth("staff")).status_code == 409
    assert c.patch(f"/drafts/{d['id']}", json={"body": "new"}, headers=auth("staff")).status_code == 409


def test_human_can_edit_in_a_new_unverified_claim_and_it_is_caught(make_client):
    c = make_client(draft_script())
    d = make_draft(c)
    edited = c.patch(f"/drafts/{d['id']}", json={"body": "Now only PKR 1!"}, headers=auth("staff")).json()
    assert edited["warnings"]


def test_approve_with_acknowledged_warnings_and_reject(make_client):
    c = make_client(draft_script(body="Huge 90% off!"))
    d = make_draft(c)
    assert c.post(f"/drafts/{d['id']}/approve", json={"acknowledge_warnings": True}, headers=auth("admin")).json()["status"] == "approved"
    c2 = make_client(draft_script())
    d2 = make_draft(c2)
    r = c2.post(f"/drafts/{d2['id']}/reject", json={"note": "tone is off"}, headers=auth("admin")).json()
    assert r["status"] == "rejected" and r["review_note"] == "tone is off"


def test_escalations_appear_for_staff_and_can_be_resolved(make_client):
    c = make_client(ScriptedLLM(call("escalate_to_human", reason="Damaged item", customer_message="arrived torn"), say("Passed to the team.")))
    r = c.post("/chat", json={"message": "my item arrived torn"}).json()
    assert r["escalated"] is True and "structured" not in r
    pending = c.get("/drafts", params={"status": "pending_review"}, headers=auth("staff")).json()["items"]
    assert [p["kind"] for p in pending] == ["support_escalation"]
    done = c.post(f"/drafts/{pending[0]['id']}/approve", json={}, headers=auth("staff")).json()
    assert done["status"] == "resolved"


# ------------------------------------------------------------------ business isolation (future multi-store)
def test_one_business_cannot_see_or_change_anothers_records(store_path, settings, make_client):
    shared = Database(make_store_engine(settings.store_url), make_agent_engine("sqlite://"))   # SAME assistant DB
    a = make_client(draft_script(), business_id="shop-a", db=shared)
    b = make_client(ScriptedLLM(), business_id="shop-b", db=shared)
    d = make_draft(a)
    assert len(a.get("/drafts", headers=auth("admin")).json()["items"]) == 1
    assert a.get("/history", headers=auth("admin")).json()["items"]
    # business B sees nothing and cannot touch A's draft
    assert b.get("/drafts", headers=auth("admin")).json()["items"] == []
    assert b.get("/history", headers=auth("admin")).json()["items"] == []
    assert b.patch(f"/drafts/{d['id']}", json={"body": "hijack"}, headers=auth("admin")).status_code == 404
    assert b.post(f"/drafts/{d['id']}/approve", json={"acknowledge_warnings": True}, headers=auth("admin")).status_code == 404
    assert b.post(f"/drafts/{d['id']}/reject", json={}, headers=auth("admin")).status_code == 404
    assert a.get("/drafts", headers=auth("admin")).json()["items"][0]["status"] == "draft"   # untouched


# ------------------------------------------------------------------ full workflow, request -> final answer
def test_end_to_end_monthly_sales_best_seller_and_promo_post(make_client, store_path):
    llm = ScriptedLLM(
        plan(("analytics", "Analyze October 2026 sales, identify the best-selling product"),
             ("marketing", "Prepare an Instagram promo post for the best seller")),
        call("period_report", period="monthly", anchor_date="2026-10-15"),
        say("Findings: October revenue PKR 14,600 from 3 orders. Best seller: Floral Sundress (OF-1002)."),
        call("get_product_details", sku="OF-1002"), call("get_confirmed_offers"),
        call("save_draft", kind="instagram_caption", title="Sundress promo", product_skus=["OF-1002"],
             body="Our October best seller, the Floral Sundress, is now PKR 4,000 - 20% off!"),
        say("Drafted an Instagram caption for review."),
    )
    c = make_client(llm)
    j = c.post("/chat", json={"message": "Analyze this month's sales, find the best-selling product and prepare a promotional post"},
               headers=auth("admin")).json()
    assert j["status"] == "completed" and j["agents_used"] == ["analytics", "marketing"]

    # the figures in the structured payload equal an independent SQL query on the shop database
    con = sqlite3.connect(store_path)
    revenue = con.execute("SELECT SUM(total) FROM orders_order WHERE status!='cancelled' "
                          "AND created_at>='2026-09-30 19:00:00' AND created_at<'2026-10-31 19:00:00'").fetchone()[0]
    con.close()
    rep = j["structured"]["tools"]["analytics"]["period_report"][0]
    assert rep["summary"]["revenue"] == revenue == 14600
    assert j["structured"]["drafts"][0]["warnings"] == []
    assert c.get("/drafts", headers=auth("admin")).json()["items"][0]["status"] == "draft"
    assert c.get("/history", headers=auth("admin")).json()["items"][0]["agents"] == ["analytics", "marketing"]
