from typing import Any
from uuid import uuid4

import httpx


def send_signal(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    user_id: str,
    device_id: str,
    platform: str,
    timezone: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "device_id": device_id,
        "user_id": user_id,
        "platform": platform,
        "user_agent": "FraudLens demo traffic client",
        "screen": {"width": 1440, "height": 900, "pixel_ratio": 1},
        "timezone": timezone,
        "language": "en-IN",
    }
    if lat is not None and lon is not None:
        payload["lat"] = lat
        payload["lon"] = lon
    response = client.post(f"{base_url}/v1/signals", headers={"X-API-Key": api_key}, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"/v1/signals returned HTTP {response.status_code}")
    return response.json()


def send_check(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    user_id: str,
    device_id: str,
    amount: float,
    payment_method: str = "card",
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "user_id": user_id,
        "device_id": device_id,
        "amount": amount,
        "currency": "INR",
        "payment_method": payment_method,
    }
    if lat is not None and lon is not None:
        payload["lat"] = lat
        payload["lon"] = lon
    response = client.post(
        f"{base_url}/v1/checks",
        headers={"X-API-Key": api_key, "Idempotency-Key": str(uuid4())},
        json=payload,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"/v1/checks returned HTTP {response.status_code}")
    return response.json()


def send_transaction(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    row: dict[str, Any],
    platform: str,
) -> dict[str, Any]:
    send_signal(
        client,
        base_url,
        api_key,
        row["user_id"],
        row["device_id"],
        platform,
        row.get("timezone", "Asia/Kolkata"),
        row.get("lat"),
        row.get("lon"),
    )
    return send_check(
        client,
        base_url,
        api_key,
        row["user_id"],
        row["device_id"],
        row["amount"],
        row.get("payment_method", "card"),
        row.get("lat"),
        row.get("lon"),
    )
