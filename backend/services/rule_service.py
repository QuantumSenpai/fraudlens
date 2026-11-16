from datetime import datetime, timezone

from services.decision_engine import calculate_rule_score
from services.rules import RuleContext, evaluate_rules
from services.rules_config import RULES_CONFIG


class RuleService:
    def evaluate(self, txn, history):
        parsed = datetime.fromisoformat(txn.timestamp.replace("Z", "+00:00"))
        now = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        known_devices = {row.get("device_id") for row in history}
        context = RuleContext(
            now=now,
            amount=txn.amount,
            user_id=txn.user_id,
            device_id=txn.device_id,
            lat=txn.lat,
            lon=txn.lon,
            user_history=history,
            known_device=txn.device_id in known_devices,
        )
        results = evaluate_rules(context, RULES_CONFIG)
        score = calculate_rule_score(results)
        triggers = [(result.rule, result.detail, result.weight) for result in results]
        return score, triggers, score >= RULES_CONFIG["scoring"]["legacy_flag_from"] or any(result.hard for result in results)


rule_service = RuleService()
