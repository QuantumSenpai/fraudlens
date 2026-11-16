import argparse
import csv
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.live_features import LIVE_FEATURE_NAMES

SEED = 42
THRESHOLD = 0.5
PAYMENT_METHODS = ("card", "netbanking", "upi", "wallet")


def find_paysim() -> Path | None:
    candidates = [ROOT / "paysim.csv", ROOT / "ml" / "data" / "paysim.csv", ROOT / "data" / "paysim.csv"]
    return next((path for path in candidates if path.is_file()), None)


def synthetic_data(rows: int = 50000) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    rng = np.random.default_rng(SEED)
    fraud = rng.binomial(1, 0.025, rows).astype(np.int8)
    amount = rng.lognormal(6.0 + fraud * 1.1, 1.0 + fraud * 0.15, rows).clip(10, 950000)
    hour = rng.integers(0, 24, rows)
    hour[fraud == 1] = np.where(rng.random((fraud == 1).sum()) < 0.48, rng.integers(0, 5, (fraud == 1).sum()), hour[fraud == 1])
    day = rng.integers(0, 7, rows)
    tx15 = rng.poisson(0.25 + fraud * 2.1, rows).astype(float)
    tx24 = (tx15 + rng.poisson(2.5 + fraud * 5.0, rows)).astype(float)
    user_mean = rng.lognormal(6.0, 0.8, rows)
    ratio = (amount / user_mean).clip(0.05, 50)
    age = rng.exponential(900, rows).clip(0, 5000)
    age[fraud == 1] *= rng.uniform(0.05, 0.7, (fraud == 1).sum())
    linked = 1 + rng.poisson(0.35 + fraud * 1.5, rows)
    distance = rng.exponential(6 + fraud * 180, rows).clip(0, 20000)
    speed = (distance / rng.uniform(0.1, 8, rows)).clip(0, 1500)
    method = rng.integers(0, 4, rows)
    one_hot = np.column_stack([method == index for index in range(4)]).astype(float)
    night = ((hour < 5) | (hour >= 23)).astype(float)
    features = np.column_stack([
        amount, np.log1p(amount), hour, day, night, tx15, tx24, ratio, age, linked,
        distance, speed, one_hot,
    ]).astype(np.float32)
    return features, fraud, {
        "source": "SYNTHETIC",
        "description": "Generated demonstration data with overlapping fraud patterns and noise; not measured transaction data.",
        "rows": str(rows),
        "payment_method_mapping": "Randomly assigned across card, netbanking, upi, wallet.",
    }


def paysim_data(path: Path, max_rows: int) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    prior: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=20))
    times: dict[str, deque[float]] = defaultdict(deque)
    features = []
    labels = []
    methods = {"PAYMENT": "upi", "TRANSFER": "netbanking", "CASH_OUT": "wallet", "CASH_IN": "card", "DEBIT": "card"}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"step", "type", "amount", "nameOrig", "isFraud"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("PaySim file must include step, type, amount, nameOrig, and isFraud")
        for row_index, row in enumerate(reader):
            if row_index >= max_rows:
                break
            user = row["nameOrig"]
            step = float(row["step"])
            amount = float(row["amount"])
            hour_float = step % 24
            hour = int(hour_float)
            day = int(step // 24) % 7
            user_times = times[user]
            while user_times and step - user_times[0] > 24:
                user_times.popleft()
            user_amounts = prior[user]
            mean = sum(value for _, value in user_amounts) / len(user_amounts) if user_amounts else amount
            ratio = amount / mean if mean else 1.0
            method = methods.get(row["type"], "card")
            one_hot = [float(method == item) for item in PAYMENT_METHODS]
            features.append([
                amount, math.log1p(amount), hour_float, day, float(hour < 5 or hour >= 23),
                0.0, float(len(user_times)), ratio, 0.0, 1.0, 0.0, 0.0, *one_hot,
            ])
            labels.append(int(float(row["isFraud"])))
            user_times.append(step)
            user_amounts.append((step, amount))
    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int8), {
        "source": "PaySim",
        "description": "PaySim synthetic mobile-money simulator data; metrics are not real-world performance.",
        "rows": str(len(labels)),
        "mapping": "amount->amount; step->hour/day; nameOrig->user history; isFraud->label. Source is hourly, so txns_last_15min is set to zero and txns_last_24h uses same-step activity.",
        "payment_method_mapping": "PAYMENT->upi, TRANSFER->netbanking, CASH_OUT->wallet, CASH_IN/DEBIT->card; this approximates payment rails because PaySim does not encode card/UPI rails.",
        "unavailable_features": "device age, distinct device users, GPS distance, and speed are set to zero/one defaults because PaySim does not provide these fields.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--max-rows", type=int, default=300000)
    parser.add_argument("--synthetic-rows", type=int, default=50000)
    args = parser.parse_args()
    dataset_path = args.dataset or find_paysim()
    if dataset_path is not None:
        x, y, dataset_info = paysim_data(dataset_path, args.max_rows)
    else:
        x, y, dataset_info = synthetic_data(args.synthetic_rows)
    if len(np.unique(y)) != 2 or int(np.sum(y)) < 2:
        raise ValueError("Training data must contain at least two examples from each class")
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=SEED, stratify=y
    )
    positive = int(np.sum(y_train))
    negative = len(y_train) - positive
    model = XGBClassifier(
        n_estimators=220,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=negative / positive,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        n_jobs=2,
        random_state=SEED,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= THRESHOLD).astype(np.int8)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    metrics = {
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "confusion_matrix": {"labels": ["legit", "fraud"], "values": [[tn, fp], [fn, tp]]},
    }
    model_dir = ROOT / "backend" / "models"
    report_path = ROOT / "ml" / "reports" / "live_v1.json"
    model_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib_path = model_dir / "xgb_live_v1.pkl"
    import joblib

    joblib.dump(model, joblib_path, compress=3)
    report = {
        "model_version": "xgb_live_v1",
        "dataset": dataset_info,
        "seed": SEED,
        "split": {"strategy": "stratified", "test_size": 0.25, "train_rows": len(y_train), "test_rows": len(y_test)},
        "threshold": THRESHOLD,
        "scale_pos_weight": negative / positive,
        "features": LIVE_FEATURE_NAMES,
        "metrics": metrics,
        "artifact": "backend/models/xgb_live_v1.pkl",
        "limitations": "Synthetic or PaySim-derived metrics are not real-world performance. This model is a demonstration baseline and requires evaluation on representative, consented merchant outcomes.",
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(joblib_path), "report": str(report_path), "dataset": dataset_info["source"], "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
