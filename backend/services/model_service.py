import joblib
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "ml" / "models" / "xgb_model.pkl"
SCALER_PATH = BASE_DIR / "ml" / "models" / "scaler.pkl"

FEATURE_ORDER = [f"V{i}" for i in range(1, 29)] + ["scaled_amount", "scaled_time"]


class ModelService:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)

    def predict(self, amount: float, time: float) -> float:
        scaled_amount = self.scaler.transform([[amount]])[0][0]
        scaled_time = self.scaler.transform([[time]])[0][0]

        row = {f"V{i}": 0.0 for i in range(1, 29)}
        row["scaled_amount"] = scaled_amount
        row["scaled_time"] = scaled_time

        df = pd.DataFrame([row], columns=FEATURE_ORDER)
        proba = self.model.predict_proba(df)[0][1]
        return float(proba)


model_service = ModelService()