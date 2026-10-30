"""Shared fixtures: a small, fully known store database (same tables as the Django shop) and a scripted fake LLM.

The fake LLM replays pre-written model turns so tests are fast, free and deterministic. It tests OUR code
(routing, tools, security, workflow). It does not test the real model's language quality.
"""
from __future__ import annotations

import copy
import datetime as dt
import uuid
from contextlib import contextmanager
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import Principal
from app.config import Settings
from app.db import Database, make_agent_engine, make_store_engine
from app.llm.base import LLMResponse, ToolCall
from app.main import create_app
from app.models_store import (Category, Color, Coupon, Order, OrderItem, Product, Shipment, Size, StoreBase, Token,
                              User, Variant)
from app.tools import ToolContext

NOW = dt.datetime(2026, 10, 28, 12, 0, tzinfo=dt.timezone.utc)
D = Decimal


# ----------------------------------------------------------------------------------------------- fake LLM
def say(text: str) -> LLMResponse:
    return LLMResponse(text=text)


def call(name: str, **inp) -> LLMResponse:
    return LLMResponse(tool_calls=[ToolCall(id="tu_" + uuid.uuid4().hex[:8], name=name, input=inp)])


def plan(*steps: tuple[str, str]) -> LLMResponse:
    return call("submit_plan", steps=[{"agent": a, "task": t} for a, t in steps])


class ScriptedLLM:
    """Pops one scripted turn per call. A turn is an LLMResponse, an Exception to raise, or a function(call_info)."""

    def __init__(self, *turns):
        self.turns, self.calls = list(turns), []

    def complete(self, *, system, messages, tools, max_tokens=1024, force_tool=None):
        self.calls.append({"system": system, "messages": copy.deepcopy(messages), "tools": tools, "force_tool": force_tool})
        if not self.turns:
            raise AssertionError("LLM was called more often than the test scripted")
        t = self.turns.pop(0)
        if isinstance(t, Exception):
            raise t
        return t(self.calls[-1]) if callable(t) else t


# ----------------------------------------------------------------------------------------------- known data
IDS = {k: uuid.uuid4() for k in ("alice", "bob", "staff", "admin", "inactive", "p1", "p2", "p3", "p4")}
TOKENS = {"alice": "tok-alice", "bob": "tok-bob", "staff": "tok-staff", "admin": "tok-admin", "inactive": "tok-inactive"}


def _build_store(path: str) -> None:
    eng = create_engine(f"sqlite:///{path}")
    StoreBase.metadata.create_all(eng)
    with Session(eng) as s:
        men, women = Category(id=uuid.uuid4(), name="T-Shirts", slug="men-tshirts", department="men"), \
                     Category(id=uuid.uuid4(), name="Dresses", slug="women-dresses", department="women")
        S, M, L = Size(id=1, label="S", order=1), Size(id=2, label="M", order=2), Size(id=3, label="L", order=3)
        black, navy = Color(id=1, name="Black"), Color(id=2, name="Navy")
        s.add_all([men, women, S, M, L, black, navy])
        s.flush()

        def prod(key, sku, name, cat, price, sale=None, active=True, desc=""):
            p = Product(id=IDS[key], name=name, slug=sku.lower(), sku=sku, category_id=cat.id, price=D(price),
                        sale_price=None if sale is None else D(sale), is_active=active,
                        description=desc or f"{name} description", material="Cotton", fit="regular",
                        care_instructions="Machine wash cold.")
            s.add(p)
            return p

        p1 = prod("p1", "OF-1001", "Essential Crew Neck Tee", men, 1000)
        p2 = prod("p2", "OF-1002", "Floral Sundress", women, 5000, sale=4000)
        p3 = prod("p3", "OF-1003", "Hidden Item", men, 999, active=False)
        p4 = prod("p4", "OF-1004", "Linen Shirt", men, 3000)
        s.flush()
        V = {}
        for key, (p, color, size, stock) in {
            "p1_bs": (p1, black, S, 10), "p1_bm": (p1, black, M, 3), "p1_nm": (p1, navy, M, 0),
            "p2_bs": (p2, black, S, 8), "p2_bl": (p2, black, L, 5),
            "p3_bs": (p3, black, S, 1),
            "p4_ns": (p4, navy, S, 0), "p4_nl": (p4, navy, L, 0),
        }.items():
            V[key] = Variant(id=uuid.uuid4(), product_id=p.id, size_id=size.id, color_id=color.id, stock=stock,
                             variant_sku=f"{p.sku}-{color.name[:3].upper()}-{size.label}")
            s.add(V[key])

        for key, email, role, active, su in [("alice", "alice@example.com", "customer", True, False),
                                             ("bob", "bob@example.com", "customer", True, False),
                                             ("staff", "staff@shop.pk", "staff", True, False),
                                             ("admin", "owner@shop.pk", "admin", True, False),
                                             ("inactive", "gone@example.com", "customer", False, False)]:
            s.add(User(id=IDS[key], email=email, role=role, is_active=active, is_superuser=su))
            s.add(Token(key=TOKENS[key], user_id=IDS[key]))

        s.add(Coupon(id=uuid.uuid4(), code="ACTIVE10", discount_type="percentage", value=D(10), min_order_amount=D(2000),
                     start_date=dt.datetime(2026, 9, 1), expiry_date=dt.datetime(2026, 12, 31), is_active=True))
        s.add(Coupon(id=uuid.uuid4(), code="EXPIRED20", discount_type="percentage", value=D(20), min_order_amount=D(0),
                     start_date=dt.datetime(2026, 1, 1), expiry_date=dt.datetime(2026, 10, 9), is_active=True))
        s.flush()

        def order(num, user, email, status, created, items, sub, ship, disc, total, ship_info=None):
            o = Order(id=uuid.uuid4(), order_number=num, user_id=IDS[user] if user else None, email=email,
                      delivery_method="standard", payment_method="cod", subtotal=D(sub), shipping_fee=D(ship),
                      discount_amount=D(disc), total=D(total), coupon_code="", status=status, created_at=created)
            s.add(o)
            s.flush()
            for v, p, qty, price in items:
                s.add(OrderItem(id=uuid.uuid4(), order_id=o.id, variant_id=V[v].id, product_name=p.name,
                                size_label="S", color_name="Black",
                                unit_price=D(price), quantity=qty))
            if ship_info:
                s.add(Shipment(order_id=o.id, **ship_info))

        order("ORD-10001", "alice", "alice@example.com", "delivered", dt.datetime(2026, 10, 5, 10, 0),
              [("p1_bs", p1, 2, 1000)], 2000, 250, 0, 2250,
              dict(carrier="TCS", tracking_number="TCS123", estimated_delivery_days="5-7",
                   shipped_at=dt.datetime(2026, 10, 6), delivered_at=dt.datetime(2026, 10, 9)))
        order("ORD-10002", None, "bob@example.com", "shipped", dt.datetime(2026, 10, 10, 8, 0),
              [("p2_bs", p2, 1, 4000)], 4000, 250, 0, 4250,
              dict(carrier="Leopards", tracking_number="LEO9", estimated_delivery_days="5-7", shipped_at=dt.datetime(2026, 10, 11)))
        order("ORD-10003", None, "bob@example.com", "cancelled", dt.datetime(2026, 10, 12, 9, 0),
              [("p1_bs", p1, 5, 1000)], 5000, 0, 0, 5000)                      # cancelled: must NOT count as sales
        # 2026-10-20 20:00 UTC == 2026-10-21 01:00 in Pakistan -> belongs to Oct 21 for the business
        order("ORD-10004", "alice", "alice@example.com", "delivered", dt.datetime(2026, 10, 20, 20, 0),
              [("p1_bm", p1, 1, 1000), ("p2_bs", p2, 2, 4000)], 9000, 0, 900, 8100)
        order("ORD-10005", None, "carol@example.com", "delivered", dt.datetime(2026, 9, 15, 10, 0),
              [("p1_bs", p1, 1, 1000)], 1000, 250, 0, 1250)
        s.commit()
    eng.dispose()


@pytest.fixture(scope="session")
def store_path(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("store") / "store.sqlite3")
    _build_store(path)
    return path


def make_settings(store_path: str, **over) -> Settings:
    base = dict(store_db_url=f"sqlite:///{store_path}", agent_db_url="sqlite://", business_id="shop-a",
                business_timezone="Asia/Karachi", anthropic_api_key="", rate_limit_per_minute=1000)
    base.update(over)
    return Settings(_env_file=None, **base)


@pytest.fixture
def settings(store_path):
    return make_settings(store_path)


@pytest.fixture
def db(settings):
    d = Database(make_store_engine(settings.store_url), make_agent_engine(settings.agent_url))
    d.init_agent_schema()
    return d


PRINCIPALS = {
    "anonymous": Principal(None, None, "anonymous"),
    "alice": Principal(IDS["alice"].hex, "alice@example.com", "customer"),
    "bob": Principal(IDS["bob"].hex, "bob@example.com", "customer"),
    "staff": Principal(IDS["staff"].hex, "staff@shop.pk", "staff"),
    "admin": Principal(IDS["admin"].hex, "owner@shop.pk", "admin"),
}


@pytest.fixture
def ctx_for(db, settings):
    """ctx_for('admin') -> context manager yielding a ToolContext (read-only shop DB + assistant DB)."""
    @contextmanager
    def factory(who: str = "admin"):
        with db.store_session() as store, db.agent_session() as agent:
            yield ToolContext(principal=PRINCIPALS[who], store=store, agent=agent, settings=settings,
                              task_id=uuid.uuid4().hex, now=NOW)
    return factory


@pytest.fixture
def make_client(store_path):
    def factory(llm=None, business_id="shop-a", db=None, **over):
        st = make_settings(store_path, business_id=business_id, **over)
        database = db or Database(make_store_engine(st.store_url), make_agent_engine(st.agent_url))
        app = create_app(st, llm=llm or ScriptedLLM(), db=database, clock=lambda: NOW)
        return TestClient(app)
    return factory


def auth(who: str) -> dict:
    return {"Authorization": f"Token {TOKENS[who]}"}
