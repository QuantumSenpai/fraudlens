from datetime import timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if not context.device_timezone or context.lat is None or context.lon is None:
        return None
    try:
        local_offset = context.now.astimezone(ZoneInfo(context.device_timezone)).utcoffset()
    except (ZoneInfoNotFoundError, ValueError):
        return None
    if local_offset is None:
        return None
    timezone_offset = local_offset.total_seconds() / 3600
    longitude_offset = context.lon / 15
    difference = abs(timezone_offset - longitude_offset)
    if difference < config["minimum_offset_difference_hours"]:
        return None
    return RuleResult(
        "GEO_DEVICE_MISMATCH",
        f"device timezone differs from GPS longitude estimate by {difference:.1f} hours",
        config["weight"],
    )
