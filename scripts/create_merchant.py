import argparse
import sys
from pathlib import Path
from secrets import token_urlsafe

backend_path = str(Path(__file__).resolve().parents[1] / "backend")
sys.path.insert(0, backend_path)

from services.auth import api_key_hash
from services.db import get_supabase


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="FraudLens Demo Merchant")
    args = parser.parse_args()
    name = args.name.strip()
    if not 1 <= len(name) <= 120:
        parser.error("merchant name must be between 1 and 120 characters")

    api_key = f"fl_{token_urlsafe(32)}"
    try:
        get_supabase().table("merchants").insert({
            "name": name,
            "api_key_hash": api_key_hash(api_key),
        }).execute()
    except Exception:
        print("Merchant creation failed; check server-side Supabase configuration and connectivity.", file=sys.stderr)
        return 1

    print("Merchant created. Save this API key; it will not be shown again:")
    print(api_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
