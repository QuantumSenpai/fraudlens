import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

RAW_PATH = os.path.join("data", "raw", "creditcard.csv")
PROCESSED_DIR = os.path.join("data", "processed")
MODELS_DIR = "models"

def load_data(path=RAW_PATH):
    return pd.read_csv(path)

def preprocess(df):
    df = df.copy()
    scaler = StandardScaler()
    df["scaled_amount"] = scaler.fit_transform(df["Amount"].values.reshape(-1, 1))
    df["scaled_time"] = scaler.fit_transform(df["Time"].values.reshape(-1, 1))
    df.drop(["Amount", "Time"], axis=1, inplace=True)

    X = df.drop("Class", axis=1)
    y = df["Class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler.pkl"))

    return X_train, X_test, y_train, y_test

if __name__ == "__main__":
    df = load_data()
    print(f"{len(df):,} transactions | Fraud: {df['Class'].sum()} ({df['Class'].mean()*100:.3f}%)")

    X_train, X_test, y_train, y_test = preprocess(df)
    print(f"Train: {X_train.shape} | Test: {X_test.shape}")

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    X_train.to_csv(os.path.join(PROCESSED_DIR, "X_train.csv"), index=False)
    X_test.to_csv(os.path.join(PROCESSED_DIR, "X_test.csv"), index=False)
    y_train.to_csv(os.path.join(PROCESSED_DIR, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(PROCESSED_DIR, "y_test.csv"), index=False)
    print(f"Saved to {PROCESSED_DIR}/")