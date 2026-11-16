from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Callable


@dataclass(frozen=True)
class RuleResult:
    rule: str
    detail: str
    weight: int
    hard: bool = False
    block: bool = False


@dataclass
class RuleContext:
    now: datetime
    amount: float
    user_id: str
    device_id: str
    lat: float | None = None
    lon: float | None = None
    user_history: list[dict[str, Any]] = field(default_factory=list)
    known_device: bool = False
    device_user_count: int = 1
    failed_payment_count: int = 0
    device_age_days: int = 0
    device_timezone: str | None = None
    device_decisions: list[str] = field(default_factory=list)


RuleFunction = Callable[[RuleContext, dict[str, Any]], RuleResult | None]


def timestamp_for(row: dict[str, Any]) -> datetime | None:
    value = row.get("created_at") or row.get("txn_timestamp") or row.get("timestamp")
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    value = sin(delta_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
    return radius * 2 * atan2(sqrt(value), sqrt(1 - value))
