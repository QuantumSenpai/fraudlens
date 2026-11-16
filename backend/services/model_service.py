import json
from pathlib import Path

import joblib
import numpy as np

from services.config import settings
from services.live_features import LIVE_FEATURE_NAMES

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
LEGACY_MODEL_PATH = MODEL_DIR / "xgb_model.json"
SCALER_PATH = MODEL_DIR / "scaler.json"
LIVE_MODEL_PATH = MODEL_DIR / "xgb_live_v1.pkl"
LEGACY_FEATURE_NAMES = [*(f"V{index}" for index in range(1, 29)), "scaled_amount", "scaled_time"]


class ModelService:
    def __init__(self, model_version: str | None = None):
        self.model = None
        self.scaler = None
        self.version = model_version or settings.model_version

    @property
    def loaded(self) -> bool:
        return self.model is not None and (self.version == "xgb_live_v1" or self.scaler is not None)

    def load(self) -> None:
        if self.version == "xgb_live_v1":
            model_path = LIVE_MODEL_PATH
            paths = (model_path,)
        elif self.version == "xgb_creditcard_v1":
            model_path = LEGACY_MODEL_PATH
            paths = (model_path, SCALER_PATH)
        else:
            raise RuntimeError(f"Unsupported MODEL_VERSION: {self.version}")
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise RuntimeError(f"Fraud model startup failed; missing model files: {', '.join(missing)}")
        try:
            if self.version == "xgb_live_v1":
                self.model = joblib.load(model_path)
                self.scaler = None
            else:
                import xgboost

                self.model = xgboost.Booster()
                self.model.load_model(model_path)
                self.scaler = json.loads(SCALER_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            self.model = None
            self.scaler = None
            raise RuntimeError("Fraud model startup failed; model artifacts could not be loaded") from exc

    def _legacy_features(self, amount: float, time: float) -> list[float]:
        if self.scaler is None:
            raise RuntimeError("Fraud model has not been loaded")
        mean = self.scaler["mean"]
        scale = self.scaler["scale"]
        scaled_amount = (amount - mean) / scale
        scaled_time = (time - mean) / scale
        return [0.0] * 28 + [float(scaled_amount), float(scaled_time)]

    def predict_with_factors(self, amount: float, time: float, live_features: list[float] | None = None) -> tuple[float, list[dict[str, float | str]]]:
        if not self.loaded:
            raise RuntimeError("Fraud model has not been loaded")
        if self.version == "xgb_live_v1":
            if live_features is None or len(live_features) != len(LIVE_FEATURE_NAMES):
                raise ValueError("Live model requires the configured live feature vector")
            values = live_features
            feature_names = LIVE_FEATURE_NAMES
        else:
            values = self._legacy_features(amount, time)
            feature_names = LEGACY_FEATURE_NAMES
        import xgboost

        row = np.asarray([values], dtype=np.float32)
        if self.version == "xgb_live_v1":
            booster = self.model.get_booster()
            matrix = xgboost.DMatrix(row, feature_names=booster.feature_names)
        else:
            booster = self.model
            matrix = xgboost.DMatrix(row, feature_names=feature_names)
        probability = float(booster.predict(matrix)[0])
        contributions = booster.predict(matrix, pred_contribs=True)[0]
        ranked = sorted(
            ((feature_names[index], float(value)) for index, value in enumerate(contributions[:-1])),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:5]
        factors = [{"feature": name, "contribution": value} for name, value in ranked]
        return probability, factors

    def predict(self, amount: float, time: float) -> float:
        return self.predict_with_factors(amount, time)[0]


model_service = ModelService()
