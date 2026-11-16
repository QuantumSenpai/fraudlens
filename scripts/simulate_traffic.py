import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.traffic_client import send_transaction

SCENARIOS = ("normal", "structuring", "velocity", "impossible_travel", "shared_device", "night_high_value", "all")


def scenario_transactions(scenario: str, run_id: str) -> list[dict[str, object]]:
    if scenario == "normal":
        user, device = f"demo-{run_id}-normal", f"demo-{run_id}-normal-device"
        return [
            {"user_id": user, "device_id": device, "amount": 250},
            {"user_id": user, "device_id": device, "amount": 375},
        ]
    if scenario == "structuring":
        user, device = f"demo-{run_id}-structuring", f"demo-{run_id}-structuring-device"
        return [{"user_id": user, "device_id": device, "amount": amount} for amount in (92000, 96000, 99000)]
    if scenario == "velocity":
        user, device = f"demo-{run_id}-velocity", f"demo-{run_id}-velocity-device"
        return [{"user_id": user, "device_id": device, "amount": amount} for amount in (350, 450, 550, 650)]
    if scenario == "impossible_travel":
        user, device = f"demo-{run_id}-travel", f"demo-{run_id}-travel-device"
        return [
            {"user_id": user, "device_id": device, "amount": 500, "lat": 12.9716, "lon": 77.5946},
            {"user_id": user, "device_id": device, "amount": 500, "lat": 28.6139, "lon": 77.2090},
        ]
    if scenario == "shared_device":
        device = f"demo-{run_id}-shared-device"
        return [
            {"user_id": f"demo-{run_id}-ring-{index}", "device_id": device, "amount": 1200 + index * 100}
            for index in range(1, 4)
        ]
    if scenario == "night_high_value":
        return [{
            "user_id": f"demo-{run_id}-night",
            "device_id": f"demo-{run_id}-night-device",
            "amount": 150000,
            "timezone": "Asia/Kolkata",
        }]
    raise ValueError(f"Unknown scenario: {scenario}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key-env", default="FRAUDLENS_API_KEY")
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--platform", choices=("web", "mobile", "extension"), default="web")
    parser.add_argument("--run-id", default=uuid4().hex[:12])
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Set the merchant API key in environment variable {args.api_key_env}")
    scenarios = ("normal", "structuring", "velocity", "impossible_travel", "shared_device", "night_high_value") if args.scenario == "all" else (args.scenario,)
    if "night_high_value" in scenarios:
        local_hour = datetime.now(ZoneInfo("Asia/Kolkata")).hour
        if not 0 <= local_hour < 5:
            print("Note: Asia/Kolkata is outside ODD_HOUR configuration (00:00-04:59); this run demonstrates high-value rules only.")
    with httpx.Client(timeout=20.0) as client:
        for scenario in scenarios:
            rows = scenario_transactions(scenario, args.run_id)
            for index, row in enumerate(rows):
                result = send_transaction(client, args.base_url.rstrip("/"), api_key, row, args.platform)
                print(json.dumps({
                    "scenario": scenario,
                    "user_id": row["user_id"],
                    "amount": row["amount"],
                    "check_id": result["check_id"],
                    "decision": result["decision"],
                    "final_score": result["final_score"],
                    "reasons": result["reasons"],
                }))
                if scenario == "impossible_travel" and index == 0:
                    time.sleep(1)


if __name__ == "__main__":
    main()
