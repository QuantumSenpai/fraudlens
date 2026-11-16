from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.user_history or context.amount <= config["threshold"]:
        return None
    return RuleResult(
        "NEW_USER_HIGH_VALUE",
        f"first transaction exceeds {config['threshold']:.2f}",
        config["weight"],
    )
