from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    current = context.now
    if context.device_timezone:
        try:
            current = current.astimezone(ZoneInfo(context.device_timezone))
        except (ZoneInfoNotFoundError, ValueError):
            pass
    if not config["start_hour"] <= current.hour < config["end_hour"]:
        return None
    timezone_name = context.device_timezone or "UTC"
    return RuleResult("ODD_HOUR", f"transaction at {current.hour:02d}:00 {timezone_name}", config["weight"])
