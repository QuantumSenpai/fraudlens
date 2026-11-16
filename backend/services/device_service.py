from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from schemas import DeviceSignalsInput
from services.db import get_supabase


def compute_trust_score(
    first_seen: datetime,
    linked_users: int,
    decisions: list[str],
    now: datetime | None = None,
) -> int:
    current = now or datetime.now(timezone.utc)
    start = first_seen if first_seen.tzinfo else first_seen.replace(tzinfo=timezone.utc)
    current = current if current.tzinfo else current.replace(tzinfo=timezone.utc)
    age_days = max(0, int((current - start).total_seconds() // 86400))
    allows = decisions.count("ALLOW")
    reviews = decisions.count("REVIEW")
    blocks = decisions.count("BLOCK")
    score = (
        50
        + min(25, age_days)
        + min(30, allows * 3)
        - min(20, reviews * 5)
        - min(45, blocks * 15)
        - min(40, max(0, linked_users - 1) * 20)
    )
    return max(0, min(100, score))


def record_device_signal(payload: DeviceSignalsInput, client_ip: str) -> dict[str, Any]:
    client = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    device: dict[str, Any] = {
        "device_id": payload.device_id,
        "last_seen": now,
        "user_agent": payload.user_agent,
        "platform": payload.platform,
        "screen": payload.screen.model_dump(exclude_none=True),
        "timezone": payload.timezone,
        "language": payload.language,
        "last_ip": client_ip,
    }
    if payload.lat is not None and payload.lon is not None:
        device["last_lat"] = payload.lat
        device["last_lon"] = payload.lon

    try:
        row = (
            client.table("devices")
            .upsert(device, on_conflict="device_id")
            .select("first_seen,last_seen")
            .single()
            .execute()
            .data
        )
        client.table("device_users").upsert(
            {"device_id": payload.device_id, "user_id": payload.user_id},
            on_conflict="device_id,user_id",
            ignore_duplicates=True,
        ).execute()
        users = (
            client.table("device_users")
            .select("user_id", count="exact")
            .eq("device_id", payload.device_id)
            .execute()
        )
        history = (
            client.table("checks")
            .select("decision")
            .eq("device_id", payload.device_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        first_seen = datetime.fromisoformat(row["first_seen"].replace("Z", "+00:00"))
        decisions = [item["decision"] for item in history.data or []]
        trust_score = compute_trust_score(first_seen, users.count or len(users.data or []), decisions)
        client.table("devices").update({"trust_score": trust_score}).eq(
            "device_id", payload.device_id
        ).execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Device signal storage is unavailable") from exc

    return {
        "device_id": payload.device_id,
        "first_seen": row["first_seen"],
        "last_seen": row["last_seen"],
        "trust_score": trust_score,
    }
