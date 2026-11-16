from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.device_user_count < config["minimum_users"]:
        return None
    return RuleResult(
        "SHARED_DEVICE",
        f"device is linked to {context.device_user_count} users",
        config["weight"],
    )
