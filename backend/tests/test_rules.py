import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.decision_engine import calculate_final_score, calculate_rule_score, resolve_decision
from services.rules.base import RuleContext
from services.rules.registry import RULES, evaluate_rules

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "rules_config.json").read_text())
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def clean_context():
    return RuleContext(
        now=NOW,
        amount=100,
        user_id="user-1",
        device_id="device-1",
        known_device=True,
        device_user_count=1,
    )


def row(amount=100, minutes_ago=1, **fields):
    return {
        "amount": amount,
        "created_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
        **fields,
    }


@pytest.mark.parametrize("name", list(RULES))
def test_each_rule_has_a_non_triggering_case(name):
    assert RULES[name](clean_context(), CONFIG["rules"][name]) is None


@pytest.mark.parametrize("name", list(RULES))
def test_each_rule_has_a_triggering_case(name):
    context = clean_context()
    config = copy.deepcopy(CONFIG["rules"][name])
    if name == "HIGH_AMOUNT":
        context.amount = config["threshold"] + 1
    elif name == "STRUCTURING":
        context.amount = config["low"]
        context.user_history = [row(config["low"]), row(config["high"], 30)]
    elif name == "VELOCITY":
        context.user_history = [row(minutes_ago=3), row(minutes_ago=2), row(minutes_ago=1)]
    elif name == "IMPOSSIBLE_TRAVEL":
        context.lat, context.lon = 0, 20
        context.user_history = [row(lat=0, lon=0, minutes_ago=60)]
    elif name == "NEW_DEVICE":
        context.known_device = False
    elif name == "ODD_HOUR":
        context.now = NOW.replace(hour=config["start_hour"])
    elif name == "SHARED_DEVICE":
        context.device_user_count = config["minimum_users"]
    elif name == "FAILED_PAYMENT_BURST":
        context.failed_payment_count = config["minimum_count"]
    elif name == "AMOUNT_SPIKE":
        context.amount = 501
        context.user_history = [row(100, minutes_ago=index + 1) for index in range(config["minimum_history"])]
    elif name == "NEW_USER_HIGH_VALUE":
        context.amount = config["threshold"] + 1
    elif name == "GEO_DEVICE_MISMATCH":
        config["enabled"] = True
        context.device_timezone = "Pacific/Honolulu"
        context.lat, context.lon = 0, 120
    elif name == "TRUSTED_DEVICE_DISCOUNT":
        context.device_age_days = config["minimum_age_days"]
        context.device_decisions = ["ALLOW"] * config["minimum_clean_decisions"]

    result = RULES[name](context, config)

    assert result is not None
    assert result.rule == name
    assert result.weight == config["weight"]


def test_rule_weights_clamp_and_hard_rules_raise_allow_to_review():
    context = clean_context()
    config = copy.deepcopy(CONFIG)
    config["rules"]["NEW_DEVICE"]["enabled"] = False
    config["rules"]["TRUSTED_DEVICE_DISCOUNT"]["enabled"] = False
    context.amount = 95000
    context.user_history = [row(95000, minutes_ago=30), row(97000, minutes_ago=60)]
    results = evaluate_rules(context, config)
    assert calculate_rule_score(results) == 35
    final_score = calculate_final_score(0, 35, config)
    assert final_score == 14
    assert resolve_decision(final_score, results, config) == "REVIEW"


@pytest.mark.parametrize(
    ("score", "hard", "expected"),
    [(29.99, False, "ALLOW"), (30, False, "REVIEW"), (59.99, False, "REVIEW"), (60, False, "BLOCK"), (0, True, "REVIEW")],
)
def test_decision_thresholds(score, hard, expected):
    from services.rules.base import RuleResult

    results = [RuleResult("STRUCTURING", "hard rule", 35, True)] if hard else []
    assert resolve_decision(score, results, CONFIG) == expected


@pytest.mark.parametrize("amount", [100000.01, 500000, 5000000, 9999999.99])
@pytest.mark.parametrize("trusted", [False, True])
def test_high_amount_requires_review_even_with_low_model_score(amount, trusted):
    context = clean_context()
    context.amount = amount
    context.user_history = [row(500000)]
    if trusted:
        context.device_age_days = 90
        context.device_decisions = ["ALLOW"] * 10
    results = evaluate_rules(context, CONFIG)
    score = calculate_final_score(2, calculate_rule_score(results), CONFIG)
    assert score < CONFIG["scoring"]["review_from"]
    assert resolve_decision(score, results, CONFIG) == "REVIEW"


@pytest.mark.parametrize("amount", [250, 100000])
def test_amount_at_or_below_high_amount_threshold_can_still_be_allowed(amount):
    context = clean_context()
    context.amount = amount
    context.user_history = [row(amount)]
    results = evaluate_rules(context, CONFIG)
    score = calculate_final_score(2, calculate_rule_score(results), CONFIG)
    assert resolve_decision(score, results, CONFIG) == "ALLOW"
