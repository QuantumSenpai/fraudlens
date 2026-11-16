from typing import Any

from services.rules.base import RuleResult


def calculate_rule_score(results: list[RuleResult]) -> int:
    return max(0, min(100, sum(result.weight for result in results)))


def calculate_final_score(ml_score: float, rule_score: int, config: dict[str, Any]) -> float:
    scoring = config["scoring"]
    return round(ml_score * scoring["ml_weight"] + rule_score * scoring["rule_weight"], 2)


def resolve_decision(final_score: float, results: list[RuleResult], config: dict[str, Any]) -> str:
    thresholds = config["scoring"]
    if final_score >= thresholds["block_from"]:
        return "BLOCK"
    if final_score >= thresholds["review_from"] or any(result.hard for result in results):
        return "REVIEW"
    return "ALLOW"
