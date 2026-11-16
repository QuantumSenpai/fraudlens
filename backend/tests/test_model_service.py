from services.live_features import LIVE_FEATURE_NAMES
from services.model_service import ModelService


def test_live_model_load_and_top_five_feature_factors():
    service = ModelService("xgb_live_v1")
    service.load()
    probability, factors = service.predict_with_factors(
        12500,
        3600,
        [12500, 9.43, 1, 0, 1, 2, 5, 4, 2, 3, 18, 360, 0, 0, 1, 0],
    )

    assert service.loaded
    assert service.version == "xgb_live_v1"
    assert 0 <= probability <= 1
    assert len(factors) == 5
    assert all(item["feature"] in LIVE_FEATURE_NAMES for item in factors)
    assert all(isinstance(item["contribution"], float) for item in factors)


def test_unknown_model_version_fails_clearly():
    service = ModelService("missing_version")

    try:
        service.load()
    except RuntimeError as exc:
        assert "Unsupported MODEL_VERSION" in str(exc)
    else:
        raise AssertionError("Unsupported model version should not load")
