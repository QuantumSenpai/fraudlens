from functools import lru_cache
from time import monotonic
from typing import Any, Literal

from fastapi import HTTPException

from schemas import ReviewInput
from services.db import get_supabase


def review_queue(status: Literal["pending", "reviewed", "all"], limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    try:
        checks = get_supabase().rpc("list_reviews", {
            "p_status": status,
            "p_limit": limit,
            "p_offset": offset,
        }).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Admin data is unavailable") from exc
    result = []
    for check in checks:
        reasons = [
            {"rule": item.get("rule"), "detail": item.get("detail"), "weight": item.get("weight")}
            for item in check.get("triggered_rules", [])
        ]
        result.append({**check, "reasons": reasons})
    return result


def resolve_review(check_id: str, payload: ReviewInput) -> dict[str, Any]:
    client = get_supabase()
    try:
        checks = (
            client.table("checks")
            .select("id,decision")
            .eq("id", check_id)
            .limit(1)
            .execute()
            .data or []
        )
        if not checks:
            raise HTTPException(status_code=404, detail="Check not found")
        if checks[0]["decision"] != "REVIEW":
            raise HTTPException(status_code=409, detail="Only REVIEW checks can be resolved")
        existing = (
            client.table("reviews")
            .select("id")
            .eq("check_id", check_id)
            .limit(1)
            .execute()
            .data or []
        )
        if existing:
            raise HTTPException(status_code=409, detail="Review has already been resolved")
        result = client.rpc("resolve_review", {
            "p_check_id": check_id,
            "p_reviewer": payload.reviewer,
            "p_outcome": payload.outcome,
            "p_note": payload.note,
        }).execute().data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Review could not be stored") from exc
    if isinstance(result, list):
        result = result[0] if result else None
    if not isinstance(result, dict):
        raise HTTPException(status_code=503, detail="Review could not be stored")
    return result


def _aggregate(name: str) -> dict[str, Any]:
    try:
        result = get_supabase().rpc(name, {}).execute().data
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Admin aggregates are unavailable") from exc
    if isinstance(result, list):
        result = result[0] if result else None
    if not isinstance(result, dict):
        raise HTTPException(status_code=503, detail="Admin aggregates are unavailable")
    return result


def admin_stats() -> dict[str, Any]:
    return _cached_admin_stats(int(monotonic() // 5))


@lru_cache(maxsize=2)
def _cached_admin_stats(_: int) -> dict[str, Any]:
    return _aggregate("admin_stats")


def evaluation() -> dict[str, Any]:
    return _aggregate("admin_evaluation")
