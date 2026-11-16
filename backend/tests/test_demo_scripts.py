import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.simulate_traffic import scenario_transactions
from scripts.smoke_test import require_result


def test_structuring_scenario_generates_three_in_range_transactions():
    rows = scenario_transactions("structuring", "run1")

    assert len(rows) == 3
    assert all(90000 <= row["amount"] <= 100000 for row in rows)
    assert len({row["user_id"] for row in rows}) == 1
    assert len({row["device_id"] for row in rows}) == 1


def test_velocity_scenario_generates_four_transactions_for_one_user():
    rows = scenario_transactions("velocity", "run2")

    assert len(rows) == 4
    assert len({row["user_id"] for row in rows}) == 1


def test_impossible_travel_scenario_has_distant_coordinate_pair():
    rows = scenario_transactions("impossible_travel", "run3")

    assert len(rows) == 2
    assert rows[0]["user_id"] == rows[1]["user_id"]
    assert rows[0]["lat"] != rows[1]["lat"]
    assert rows[0]["lon"] != rows[1]["lon"]


def test_shared_device_scenario_links_three_users_to_one_device():
    rows = scenario_transactions("shared_device", "run4")

    assert len(rows) == 3
    assert len({row["user_id"] for row in rows}) == 3
    assert len({row["device_id"] for row in rows}) == 1


def test_night_high_value_scenario_uses_new_user_high_amount():
    rows = scenario_transactions("night_high_value", "run5")

    assert len(rows) == 1
    assert rows[0]["amount"] > 100000
    assert rows[0]["timezone"] == "Asia/Kolkata"


def test_smoke_test_explains_legacy_model_block_limitation():
    try:
        require_result({"decision": "REVIEW", "model_version": "xgb_creditcard_v1", "final_score": 40}, "BLOCK", "high-risk")
    except SystemExit as exc:
        assert "MODEL_VERSION=xgb_live_v1" in str(exc)
    else:
        raise AssertionError("smoke test should explain why the fallback model did not block")
