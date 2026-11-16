import hashlib
import hmac
from typing import Annotated, Any

from fastapi import Header, HTTPException

from services.config import settings
from services.db import get_supabase


def api_key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def require_merchant(api_key: Annotated[str | None, Header(alias="X-API-Key")] = None) -> dict[str, Any]:
    if not api_key or not 16 <= len(api_key) <= 128:
        raise HTTPException(status_code=401, detail="Invalid API key")

    digest = api_key_hash(api_key)
    try:
        response = (
            get_supabase()
            .table("merchants")
            .select("id,api_key_hash,is_active")
            .eq("api_key_hash", digest)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Merchant authentication is unavailable") from exc

    merchant = next(iter(response.data or []), None)
    if merchant is None or not hmac.compare_digest(merchant["api_key_hash"], digest):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return merchant


def require_admin(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured")
    scheme, separator, token = (authorization or "").partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not token
        or not hmac.compare_digest(api_key_hash(token), api_key_hash(settings.admin_token))
    ):
        raise HTTPException(status_code=401, detail="Invalid admin token")


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required and must be at most 128 characters")
    return idempotency_key
