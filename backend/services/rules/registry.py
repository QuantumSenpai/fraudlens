from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import Any

from services.rules.base import RuleContext, RuleResult

_RULE_DIR = Path(__file__).resolve().parent
RULES = {
    module.name.upper(): getattr(import_module(f"{__package__}.{module.name}"), "evaluate")
    for module in iter_modules([str(_RULE_DIR)])
    if module.name not in {"base", "registry"}
}


def evaluate_rules(context: RuleContext, config: dict[str, Any]) -> list[RuleResult]:
    results = []
    for name, evaluate in RULES.items():
        rule_config = config["rules"][name]
        if rule_config["enabled"]:
            result = evaluate(context, rule_config)
            if result is not None:
                results.append(result)
    return results
