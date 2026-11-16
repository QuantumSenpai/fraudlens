from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    minimum = config["minimum_clean_decisions"]
    if (
        context.device_age_days < config["minimum_age_days"]
        or context.device_decisions.count("ALLOW") < minimum
        or any(decision != "ALLOW" for decision in context.device_decisions)
    ):
        return None
    return RuleResult(
        "TRUSTED_DEVICE_DISCOUNT",
        f"device is {context.device_age_days} days old with {minimum} or more clean decisions",
        config["weight"],
    )
