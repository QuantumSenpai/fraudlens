from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

HIGH_AMOUNT_THRESHOLD = 100000
STRUCTURING_LOW = 90000
STRUCTURING_HIGH = 100000
VELOCITY_WINDOW_MIN = 15
VELOCITY_COUNT = 4
IMPOSSIBLE_SPEED_KMH = 1000
IMPOSSIBLE_MIN_DIST_KM = 50
ODD_HOUR_START = 0
ODD_HOUR_END = 5

FLAG_THRESHOLD = 40


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


class RuleService:
    def evaluate(self, txn, history):
        triggers = []
        ts = datetime.fromisoformat(txn.timestamp).replace(tzinfo=None)

        def parse_ts(value):
            return datetime.fromisoformat(value).replace(tzinfo=None)

        if txn.amount > HIGH_AMOUNT_THRESHOLD:
            triggers.append(("HIGH_AMOUNT", f"amount {txn.amount} exceeds threshold", 25))

        recent_structuring = [
            h for h in history
            if STRUCTURING_LOW <= float(h["amount"]) <= STRUCTURING_HIGH
            and ts - parse_ts(h["txn_timestamp"]) <= timedelta(hours=24)
        ]
        if STRUCTURING_LOW <= txn.amount <= STRUCTURING_HIGH:
            recent_structuring.append({"amount": txn.amount})
        if len(recent_structuring) >= 3:
            triggers.append(("STRUCTURING", f"{len(recent_structuring)} txns near threshold in 24h", 35))

        recent_velocity = [
            h for h in history
            if ts - parse_ts(h["txn_timestamp"]) <= timedelta(minutes=VELOCITY_WINDOW_MIN)
        ]
        if len(recent_velocity) + 1 >= VELOCITY_COUNT:
            triggers.append(("VELOCITY", f"{len(recent_velocity) + 1} txns within {VELOCITY_WINDOW_MIN} min", 30))

        if history:
            last = history[0]
            dist = haversine(float(last["lat"]), float(last["lon"]), txn.lat, txn.lon)
            hours = (ts - parse_ts(last["txn_timestamp"])).total_seconds() / 3600
            if hours > 0 and dist > IMPOSSIBLE_MIN_DIST_KM:
                speed = dist / hours
                if speed > IMPOSSIBLE_SPEED_KMH:
                    triggers.append(("IMPOSSIBLE_TRAVEL", f"{dist:.0f}km in {hours*60:.1f}min implies {speed:.0f}km/h", 40))

        known_devices = {h["device_id"] for h in history}
        if txn.device_id not in known_devices:
            triggers.append(("NEW_DEVICE", f"first txn from device {txn.device_id}", 15))

        if ODD_HOUR_START <= ts.hour < ODD_HOUR_END:
            triggers.append(("ODD_HOUR", f"txn at {ts.hour}:00", 10))

        score = min(sum(w for _, _, w in triggers), 100)
        return score, triggers, score >= FLAG_THRESHOLD


rule_service = RuleService()