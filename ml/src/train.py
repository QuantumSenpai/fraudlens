import os
import time
import joblib
import pandas as pd
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)

PROCESSED_DIR = os.path.join("data", "processed")
MODELS_DIR = "models"

def load_processed():
    X_train = pd.read_csv(os.path.join(PROCESSED_DIR, "X_train.csv"))
    X_test = pd.read_csv(os.path.join(PROCESSED_DIR, "X_test.csv"))
    y_train = pd.read_csv(os.path.join(PROCESSED_DIR, "y_train.csv")).squeeze()
    y_test = pd.read_csv(os.path.join(PROCESSED_DIR, "y_test.csv")).squeeze()
    return X_train, X_test, y_train, y_test

def apply_smote(X_train, y_train):
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X_train, y_train)
    return X_res, y_res

def evaluate(name, model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print(f"\n{'='*50}\n{name}\n{'='*50}")
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")
    print(f"PR-AUC (AUPRC): {average_precision_score(y_test, y_prob):.4f}")

    return {
        "model": name,
        "roc_auc": roc_auc_score(y_test, y_prob),
        "pr_auc": average_precision_score(y_test, y_prob),
    }

def train_all(X_train, y_train, X_test, y_test):
    results = []

    log_reg = LogisticRegression(max_iter=1000, random_state=42)
    log_reg.fit(X_train, y_train)
    results.append(evaluate("Logistic Regression", log_reg, X_test, y_test))

    rf = RandomForestClassifier(n_estimators=100, max_depth=10, n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    results.append(evaluate("Random Forest", rf, X_test, y_test))

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="aucpr",
        n_jobs=-1,
        random_state=42,
    )
    xgb.fit(X_train, y_train)
    results.append(evaluate("XGBoost", xgb, X_test, y_test))

    return xgb, results

if __name__ == "__main__":
    start = time.time()

    X_train, X_test, y_train, y_test = load_processed()
    print(f"Before SMOTE: {y_train.value_counts().to_dict()}")

    X_train_res, y_train_res = apply_smote(X_train, y_train)
    print(f"After SMOTE: {pd.Series(y_train_res).value_counts().to_dict()}")

    best_model, results = train_all(X_train_res, y_train_res, X_test, y_test)

    print(f"\n{'='*50}\nSUMMARY\n{'='*50}")
    for r in results:
        print(f"{r['model']:<20} ROC-AUC: {r['roc_auc']:.4f}  PR-AUC: {r['pr_auc']:.4f}")

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(best_model, os.path.join(MODELS_DIR, "xgb_model.pkl"))
    print(f"\nBest model (XGBoost) saved to {MODELS_DIR}/xgb_model.pkl")
    print(f"Total time: {time.time() - start:.1f}s")