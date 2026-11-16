from functools import lru_cache

from fastapi import HTTPException
from supabase import Client, create_client

from services.config import settings


@lru_cache(maxsize=1)
def _client() -> Client | None:
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def get_supabase() -> Client:
    client = _client()
    if client is None:
        raise HTTPException(status_code=503, detail="Database is not configured")
    return client


def db_reachable() -> bool:
    try:
        get_supabase().table("transactions").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def get_user_history(user_id: str, limit: int = 50):
    response = (
        get_supabase().table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("txn_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def insert_transaction(txn, rule_score, ml_score, final_score, flagged):
    get_supabase().table("transactions").insert(
        {
            "user_id": txn.user_id,
            "device_id": txn.device_id,
            "amount": txn.amount,
            "txn_time": txn.time,
            "lat": txn.lat,
            "lon": txn.lon,
            "txn_timestamp": txn.timestamp,
            "rule_score": rule_score,
            "ml_score": ml_score,
            "final_score": final_score,
            "flagged": flagged,
        }
    ).execute()
