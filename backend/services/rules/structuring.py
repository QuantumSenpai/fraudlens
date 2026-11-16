from datetime import timedelta
from typing import Any

from services.rules.base import RuleContext, RuleResult, timestamp_for


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    low, high = config["low"], config["high"]
    cutoff = context.now - timedelta(hours=config["window_hours"])
    count = sum(
        low <= float(row.get("amount", 0)) <= high
        and (timestamp := timestamp_for(row)) is not None
        and cutoff <= timestamp <= context.now
        for row in context.user_history
    )
    count += int(low <= context.amount <= high)
    if count < config["minimum_count"]:
        return None
    return RuleResult(
        "STRUCTURING",
        f"{count} transactions between {low:.0f} and {high:.0f} within {config['window_hours']} hours",
        config["weight"],
        config.get("hard", False),
    )
