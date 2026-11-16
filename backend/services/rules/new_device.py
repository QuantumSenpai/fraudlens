from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.known_device:
        return None
    return RuleResult("NEW_DEVICE", f"first transaction from device {context.device_id}", config["weight"])
