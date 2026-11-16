from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.amount <= config["threshold"]:
        return None
    return RuleResult("HIGH_AMOUNT", f"amount {context.amount:.2f} exceeds {config['threshold']:.2f}", config["weight"])
