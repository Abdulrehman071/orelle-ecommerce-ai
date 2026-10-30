"""Documented schema setup:  python -m app.init_db   (creates the assistant's own tables; never touches the shop DB)."""
from .config import get_settings
from .db import Database

if __name__ == "__main__":
    s = get_settings()
    Database.from_settings(s).init_agent_schema()
    print(f"Assistant tables ready at {s.agent_url}")
