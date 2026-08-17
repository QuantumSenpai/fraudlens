import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user_history(user_id: str, limit: int = 50):
    response = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("txn_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def insert_transaction(txn, rule_score, ml_score, final_score, flagged):
    supabase.table("transactions").insert(
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