from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    amounts = [float(row["amount"]) for row in context.user_history[:config["history_limit"]] if float(row.get("amount", 0)) > 0]
    if len(amounts) < config["minimum_history"]:
        return None
    average = sum(amounts) / len(amounts)
    if context.amount <= config["average_multiplier"] * average:
        return None
    return RuleResult(
        "AMOUNT_SPIKE",
        f"amount {context.amount:.2f} is over {config['average_multiplier']}x the recent average {average:.2f}",
        config["weight"],
    )
