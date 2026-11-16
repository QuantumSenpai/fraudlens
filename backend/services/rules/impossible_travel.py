from typing import Any

from services.rules.base import RuleContext, RuleResult, haversine_km, timestamp_for


def evaluate(context: RuleContext, config: dict[str, Any]) -> RuleResult | None:
    if context.lat is None or context.lon is None:
        return None
    for row in context.user_history:
        if row.get("lat") is None or row.get("lon") is None:
            continue
        timestamp = timestamp_for(row)
        if timestamp is None:
            continue
        hours = (context.now - timestamp).total_seconds() / 3600
        distance = haversine_km(float(row["lat"]), float(row["lon"]), context.lat, context.lon)
        if hours > 0 and distance > config["minimum_distance_km"]:
            speed = distance / hours
            if speed > config["minimum_speed_kmh"]:
                return RuleResult(
                    "IMPOSSIBLE_TRAVEL",
                    f"{distance:.0f}km in {hours * 60:.1f} minutes implies {speed:.0f}km/h",
                    config["weight"],
                    config.get("hard", False),
                )
    return None
