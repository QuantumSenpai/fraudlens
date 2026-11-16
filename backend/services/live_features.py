from datetime import datetime, timedelta, timezone
from math import log1p
from typing import Any

from services.rules.base import haversine_km, timestamp_for

LIVE_FEATURE_NAMES = [
    "amount",
    "log_amount",
    "hour",
    "day_of_week",
    "is_night",
    "txns_last_15min",
    "txns_last_24h",
    "amount_ratio_to_user_mean",
    "device_age_hours",
    "device_user_count",
    "distance_from_last_txn_km",
    "speed_kmh",
    "payment_method_card",
    "payment_method_netbanking",
    "payment_method_upi",
    "payment_method_wallet",
]


def build_live_features(
    amount: float,
    now: datetime,
    payment_method: str | None,
    history: list[dict[str, Any]],
    device_age_hours: float,
    device_user_count: int,
    current_lat: float | None = None,
    current_lon: float | None = None,
) -> list[float]:
    current = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    ordered = []
    for row in history:
        timestamp = timestamp_for(row)
        if timestamp is not None and timestamp <= current:
            ordered.append((timestamp, row))
    ordered.sort(key=lambda item: item[0], reverse=True)
    recent_15 = 0
    recent_24 = 0
    amounts = []
    last_location = None
    for timestamp, row in ordered:
        age = current - timestamp
        if age <= timedelta(minutes=15):
            recent_15 += 1
        if age <= timedelta(hours=24):
            recent_24 += 1
        try:
            previous_amount = float(row.get("amount", 0))
        except (TypeError, ValueError):
            previous_amount = 0
        if previous_amount > 0 and len(amounts) < 20:
            amounts.append(previous_amount)
        if last_location is None and row.get("lat") is not None and row.get("lon") is not None:
            if age.total_seconds() > 0:
                last_location = (timestamp, float(row["lat"]), float(row["lon"]))

    average = sum(amounts) / len(amounts) if amounts else amount
    ratio = amount / average if average > 0 else 1.0
    distance = 0.0
    speed = 0.0
    if last_location is not None and current_lat is not None and current_lon is not None:
        timestamp, lat, lon = last_location
        distance = haversine_km(lat, lon, current_lat, current_lon)
        hours = (current - timestamp).total_seconds() / 3600
        if hours > 0:
            speed = distance / hours

    hour = current.hour
    values = [
        amount,
        log1p(amount),
        float(hour),
        float(current.weekday()),
        float(hour < 5 or hour >= 23),
        float(recent_15),
        float(recent_24),
        ratio,
        max(0.0, device_age_hours),
        float(max(0, device_user_count)),
        distance,
        speed,
    ]
    values.extend(float(payment_method == method) for method in ("card", "netbanking", "upi", "wallet"))
    return values
