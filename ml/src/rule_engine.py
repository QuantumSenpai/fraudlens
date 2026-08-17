from datetime import timedelta
from math import radians, sin, cos, sqrt, atan2

HIGH_AMOUNT_THRESHOLD = 100000
STRUCTURING_THRESHOLD = 90000
STRUCTURING_COUNT = 3
STRUCTURING_WINDOW_HOURS = 24
VELOCITY_WINDOW_MINUTES = 15
VELOCITY_COUNT_LIMIT = 4
IMPOSSIBLE_TRAVEL_SPEED_KMH = 1000
ODD_HOUR_START = 0
ODD_HOUR_END = 5

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


class RuleEngine:
    def __init__(self):
        self.user_history = {}
        self.known_devices = {}

    def _recent(self, user_id, current_time, minutes):
        history = self.user_history.get(user_id, [])
        cutoff = current_time - timedelta(minutes=minutes)
        return [t for t in history if t["timestamp"] >= cutoff]

    def check_high_amount(self, txn):
        if txn["amount"] > HIGH_AMOUNT_THRESHOLD:
            return {"rule": "HIGH_AMOUNT", "triggered": True, "weight": 25,
                    "message": f"Amount {txn['amount']} exceeds threshold {HIGH_AMOUNT_THRESHOLD}"}
        return {"rule": "HIGH_AMOUNT", "triggered": False, "weight": 0}

    def check_structuring(self, txn):
        recent = self._recent(txn["user_id"], txn["timestamp"], STRUCTURING_WINDOW_HOURS * 60)
        near_threshold = [t for t in recent if STRUCTURING_THRESHOLD <= t["amount"] <= HIGH_AMOUNT_THRESHOLD]
        if len(near_threshold) >= STRUCTURING_COUNT:
            return {"rule": "STRUCTURING", "triggered": True, "weight": 35,
                    "message": f"{len(near_threshold)} transactions just under reporting threshold in {STRUCTURING_WINDOW_HOURS}h"}
        return {"rule": "STRUCTURING", "triggered": False, "weight": 0}

    def check_velocity(self, txn):
        recent = self._recent(txn["user_id"], txn["timestamp"], VELOCITY_WINDOW_MINUTES)
        if len(recent) >= VELOCITY_COUNT_LIMIT:
            return {"rule": "VELOCITY", "triggered": True, "weight": 30,
                    "message": f"{len(recent)} transactions within {VELOCITY_WINDOW_MINUTES} min"}
        return {"rule": "VELOCITY", "triggered": False, "weight": 0}

    def check_impossible_travel(self, txn):
        history = self.user_history.get(txn["user_id"], [])
        if history and "lat" in txn and "lon" in txn:
            last = history[-1]
            if "lat" in last and "lon" in last:
                dist_km = haversine_km(last["lat"], last["lon"], txn["lat"], txn["lon"])
                hours = max((txn["timestamp"] - last["timestamp"]).total_seconds() / 3600, 1e-6)
                speed_kmh = dist_km / hours
                if speed_kmh > IMPOSSIBLE_TRAVEL_SPEED_KMH and dist_km > 50:
                    return {"rule": "IMPOSSIBLE_TRAVEL", "triggered": True, "weight": 40,
                            "message": f"Implied speed {speed_kmh:.0f} km/h across {dist_km:.0f} km"}
        return {"rule": "IMPOSSIBLE_TRAVEL", "triggered": False, "weight": 0}

    def check_new_device(self, txn):
        user_id = txn["user_id"]
        device = txn.get("device_id")
        if device:
            known = self.known_devices.setdefault(user_id, set())
            if known and device not in known:
                known.add(device)
                return {"rule": "NEW_DEVICE", "triggered": True, "weight": 15,
                        "message": f"First transaction from device {device}"}
            known.add(device)
        return {"rule": "NEW_DEVICE", "triggered": False, "weight": 0}

    def check_odd_hour(self, txn):
        hour = txn["timestamp"].hour
        if ODD_HOUR_START <= hour < ODD_HOUR_END:
            return {"rule": "ODD_HOUR", "triggered": True, "weight": 10,
                    "message": f"Transaction at {hour}:00, outside normal hours"}
        return {"rule": "ODD_HOUR", "triggered": False, "weight": 0}

    def evaluate(self, txn):
        checks = [
            self.check_high_amount(txn),
            self.check_structuring(txn),
            self.check_velocity(txn),
            self.check_impossible_travel(txn),
            self.check_new_device(txn),
            self.check_odd_hour(txn),
        ]
        triggered = [c for c in checks if c["triggered"]]
        rule_score = min(sum(c["weight"] for c in triggered), 100)

        self.user_history.setdefault(txn["user_id"], []).append(txn)

        return {"rule_score": rule_score, "triggered_rules": triggered, "flagged": rule_score >= 40}


if __name__ == "__main__":
    from datetime import datetime

    engine = RuleEngine()

    txn1 = {"user_id": "u1", "amount": 5000, "lat": 22.5726, "lon": 88.3639,
            "device_id": "dev_A", "timestamp": datetime(2026, 1, 1, 14, 0, 0)}
    txn2 = {"user_id": "u1", "amount": 150000, "lat": 28.7041, "lon": 77.1025,
            "device_id": "dev_B", "timestamp": datetime(2026, 1, 1, 14, 5, 0)}

    print(engine.evaluate(txn1))
    print(engine.evaluate(txn2))