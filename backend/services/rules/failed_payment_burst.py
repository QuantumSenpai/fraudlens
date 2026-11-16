from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.failed_payment_count < config["minimum_count"]:
        return None
    return RuleResult(
        "FAILED_PAYMENT_BURST",
        f"{context.failed_payment_count} failed payments within {config['window_minutes']} minutes",
        config["weight"],
    )
