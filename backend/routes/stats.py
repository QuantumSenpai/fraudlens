from fastapi import APIRouter
from services.db import supabase

router = APIRouter()


@router.get("/stats")
def stats():
    total = supabase.table("transactions").select("id", count="exact").execute()
    flagged = supabase.table("transactions").select("id", count="exact").eq("flagged", True).execute()
    recent = (
        supabase.table("transactions")
        .select("*")
        .order("txn_timestamp", desc=True)
        .limit(10)
        .execute()
    )

    total_count = total.count or 0
    flagged_count = flagged.count or 0
    flagged_rate = round((flagged_count / total_count) * 100, 2) if total_count else 0

    return {
        "total_transactions": total_count,
        "flagged_transactions": flagged_count,
        "flagged_rate_percent": flagged_rate,
        "recent_transactions": recent.data,
    }