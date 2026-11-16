from typing import Any

from services.rules.base import RuleContext, RuleResult


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.amount >= config.get("block_threshold", float("inf")):
        return RuleResult(
            "HIGH_AMOUNT",
            f"amount {context.amount:.2f} meets or exceeds hard limit {config['block_threshold']:.2f}; payment blocked",
            config["weight"],
            hard=True,
            block=True,
        )
    if context.amount <= config["threshold"]:
        return None
    return RuleResult(
        "HIGH_AMOUNT",
        f"amount {context.amount:.2f} exceeds {config['threshold']:.2f}"
        + ("; reviewer approval required" if config.get("hard", False) else ""),
        config["weight"],
        config.get("hard", False),
    )
