from fastapi import APIRouter
from services.db import supabase

router = APIRouter()


@router.get("/history/{user_id}")
def history(user_id: str, limit: int = 20):
    response = (
        supabase.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("txn_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data