from datetime import timedelta
from typing import Any

from services.rules.base import RuleContext, RuleResult, timestamp_for


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    cutoff = context.now - timedelta(minutes=config["window_minutes"])
    count = sum(
        (timestamp := timestamp_for(row)) is not None and cutoff <= timestamp <= context.now
        for row in context.user_history
    ) + 1
    if count < config["minimum_count"]:
        return None
    return RuleResult("VELOCITY", f"{count} transactions within {config['window_minutes']} minutes", config["weight"])
