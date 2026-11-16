import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.traffic_client import send_signal, send_transaction


def require_result(result: dict, expected: str, label: str) -> None:
    if result["decision"] != expected:
        message = (
            f"{label} expected {expected}, got {result['decision']} "
            f"(model={result['model_version']}, final_score={result['final_score']})"
        )
        if label == "high-risk" and result["model_version"] == "xgb_creditcard_v1":
            message += "; select MODEL_VERSION=xgb_live_v1 for a live-feature BLOCK smoke case"
        raise SystemExit(message)
    print(json.dumps({"case": label, "check_id": result["check_id"], "decision": result["decision"], "final_score": result["final_score"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--api-key-env", default="FRAUDLENS_API_KEY")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Set the merchant API key in environment variable {args.api_key_env}")
    base_url = args.base_url.rstrip("/")
    run_id = uuid4().hex[:12]
    with httpx.Client(timeout=20.0) as client:
        health_response = client.get(f"{base_url}/health")
        if health_response.status_code != 200:
            raise SystemExit(f"/health returned HTTP {health_response.status_code}")
        health = health_response.json()
        if not health.get("model_loaded") or not health.get("db_reachable"):
            raise SystemExit("/health did not report a loaded model and reachable database")
        print(json.dumps({"case": "health", **health}))
        allow_row = {
            "user_id": f"smoke-{run_id}-allow",
            "device_id": f"smoke-{run_id}-allow-device",
            "amount": 250,
        }
        allow_result = send_transaction(client, base_url, api_key, allow_row, "web")
        require_result(allow_result, "ALLOW", "low-risk")
        block_user = f"smoke-{run_id}-block"
        block_device = f"smoke-{run_id}-ring-device"
        for index in range(3):
            send_signal(client, base_url, api_key, f"smoke-{run_id}-ring-{index}", block_device, "web", "Asia/Kolkata")
        for amount in (92000, 94000, 96000, 98000, 99000):
            send_transaction(client, base_url, api_key, {
                "user_id": block_user,
                "device_id": block_device,
                "amount": amount,
            }, "web")
        block_result = send_transaction(client, base_url, api_key, {
            "user_id": block_user,
            "device_id": block_device,
            "amount": 999999,
        }, "web")
        require_result(block_result, "BLOCK", "high-risk")


if __name__ == "__main__":
    main()
