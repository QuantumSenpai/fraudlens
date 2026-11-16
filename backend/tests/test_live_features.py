from datetime import datetime, timedelta, timezone

from services.live_features import LIVE_FEATURE_NAMES, build_live_features


def test_live_feature_order_counts_ratio_and_payment_method():
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    history = [
        {"amount": 100, "created_at": (now - timedelta(minutes=5)).isoformat()},
        {"amount": 200, "created_at": (now - timedelta(hours=3)).isoformat()},
    ]

    features = build_live_features(
        600,
        now,
        "upi",
        history,
        device_age_hours=48,
        device_user_count=3,
    )

    assert len(features) == len(LIVE_FEATURE_NAMES) == 16
    assert features[:12] == [600, features[1], 12.0, 0.0, 0.0, 1.0, 2.0, 4.0, 48.0, 3.0, 0.0, 0.0]
    assert features[12:] == [0.0, 0.0, 1.0, 0.0]


def test_live_feature_location_is_from_last_valid_history_location():
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    previous = now - timedelta(hours=2)
    history = [
        {"amount": 100, "created_at": (now - timedelta(minutes=5)).isoformat()},
        {"amount": 200, "lat": 12.0, "lon": 77.0, "created_at": previous.isoformat()},
    ]

    features = build_live_features(
        100,
        now,
        "card",
        history,
        device_age_hours=1,
        device_user_count=1,
        current_lat=13.0,
        current_lon=78.0,
    )

    assert features[10] > 0
    assert features[11] > 0
    assert features[12:] == [1.0, 0.0, 0.0, 0.0]
