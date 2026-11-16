from fastapi import APIRouter, Depends, Request

from schemas import CheckInput, CheckResponse
from services.auth import require_idempotency_key, require_merchant
from services.check_service import create_check
from services.client_ip import resolve_client_ip
from services.rate_limit import rate_limiter

router = APIRouter()


@router.post("/v1/checks", response_model=CheckResponse)
def check(
    payload: CheckInput,
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
    merchant: dict = Depends(require_merchant),
):
    client_ip = resolve_client_ip(request)
    rate_limiter.enforce(
        "checks",
        str(merchant["id"]),
        client_ip,
        limit=60,
        window_seconds=60,
    )
    return create_check(payload, str(merchant["id"]), idempotency_key, client_ip)
