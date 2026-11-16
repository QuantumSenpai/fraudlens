from fastapi import APIRouter, Depends
from services.auth import require_merchant
from services.db import get_supabase

router = APIRouter(dependencies=[Depends(require_merchant)])


@router.get("/history/{user_id}")
def history(user_id: str, limit: int = 20):
    response = (
        get_supabase().table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("txn_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data
