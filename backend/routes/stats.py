from fastapi import APIRouter, Depends
from fastapi import HTTPException
from services.auth import require_admin
from services.db import get_supabase

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/stats")
def stats():
    try:
        return get_supabase().rpc("legacy_stats", {}).execute().data
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Legacy statistics are unavailable") from exc
