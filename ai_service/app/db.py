"""Two separate databases:

* STORE database  - the existing Django shop database. The assistant opens it READ-ONLY.
* AGENT database  - the assistant's own tables (tasks, tool logs, drafts). Read/write.

Keeping them apart means a bug or a prompt-injection attack in the assistant can never change
products, stock, prices or orders.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class StoreReadOnlyError(RuntimeError):
    """Raised if anything tries to write to the shop database."""


def _is_sqlite(url) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def make_store_engine(url) -> Engine:
    kwargs = {"connect_args": {"timeout": 10, "check_same_thread": False}} if _is_sqlite(url) else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)

    if _is_sqlite(url):
        @event.listens_for(engine, "connect")
        def _query_only(dbapi_conn, _record):  # SQLite itself refuses writes on this connection
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA query_only = ON")
            cur.close()

    @event.listens_for(engine, "before_cursor_execute")
    def _only_reads(conn, cursor, statement, parameters, context, executemany):  # second safety net (any DB)
        if not statement.lstrip().upper().startswith(("SELECT", "WITH", "PRAGMA")):
            raise StoreReadOnlyError(f"The shop database is read-only; blocked statement: {statement[:60]!r}")

    return engine


def make_agent_engine(url) -> Engine:
    if _is_sqlite(url):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if make_url(url).database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool  # one shared in-memory DB
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


@dataclass
class Database:
    store_engine: Engine
    agent_engine: Engine

    def __post_init__(self):
        self._store = sessionmaker(self.store_engine, expire_on_commit=False)
        self._agent = sessionmaker(self.agent_engine, expire_on_commit=False)

    @classmethod
    def from_settings(cls, settings) -> "Database":
        return cls(make_store_engine(settings.store_url), make_agent_engine(settings.agent_url))

    def init_agent_schema(self) -> None:
        from .models_agent import AgentBase
        AgentBase.metadata.create_all(self.agent_engine)

    @contextmanager
    def store_session(self):
        s: Session = self._store()
        try:
            yield s
        finally:
            s.close()

    @contextmanager
    def agent_session(self):
        s: Session = self._agent()
        try:
            yield s
        finally:
            s.close()
