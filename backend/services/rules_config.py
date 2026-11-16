import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[1] / "rules_config.json"
RULES_CONFIG: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
