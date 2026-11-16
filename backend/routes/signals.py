from fastapi import APIRouter, Depends, Request

from schemas import DeviceSignalsInput, DeviceSignalsResponse
from services.auth import require_merchant
from services.client_ip import resolve_client_ip
from services.device_service import record_device_signal

router = APIRouter(dependencies=[Depends(require_merchant)])


@router.post("/v1/signals", response_model=DeviceSignalsResponse)
def collect_signals(payload: DeviceSignalsInput, request: Request):
    return record_device_signal(payload, resolve_client_ip(request, payload.ip_override))
