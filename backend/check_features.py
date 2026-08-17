import joblib

scaler = joblib.load("../ml/models/scaler.pkl")
model = joblib.load("../ml/models/xgb_model.pkl")

print("scaler expects:", scaler.n_features_in_)
if hasattr(scaler, "feature_names_in_"):
    print("scaler feature names:", list(scaler.feature_names_in_))

print("model expects:", model.n_features_in_)
booster = model.get_booster()
print("model feature names:", booster.feature_names)