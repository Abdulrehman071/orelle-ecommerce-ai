"""Business-policy source of truth (see data/store_policies.json)."""
from __future__ import annotations

import json
from functools import lru_cache

from .config import SERVICE_DIR


@lru_cache
def load_policies() -> dict:
    with open(SERVICE_DIR / "data" / "store_policies.json", encoding="utf-8") as f:
        return json.load(f)
