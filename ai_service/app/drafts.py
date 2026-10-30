from __future__ import annotations

from .models_agent import Draft


def draft_view(d: Draft) -> dict:
    return {
        "id": d.id, "kind": d.kind, "title": d.title, "body": d.body, "status": d.status,
        "warnings": d.warnings or [], "product_skus": d.product_skus or [], "meta": d.meta or {},
        "created_at": d.created_at.isoformat() + "Z" if d.created_at else None,
        "updated_at": d.updated_at.isoformat() + "Z" if d.updated_at else None,
        "review_note": d.review_note or "",
    }
