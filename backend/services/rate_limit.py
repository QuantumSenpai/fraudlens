from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException


class RateLimiter:
    def __init__(self):
        self._events: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()
        self._next_cleanup = 0.0

    def enforce(
        self,
        scope: str,
        merchant_id: str,
        client_ip: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate limits must be positive")

        now = monotonic()
        keys = ((scope, f"merchant:{merchant_id}"), (scope, f"ip:{client_ip}"))
        with self._lock:
            if now >= self._next_cleanup:
                for key, events in list(self._events.items()):
                    while events and events[0] <= now - window_seconds:
                        events.popleft()
                    if not events:
                        del self._events[key]
                self._next_cleanup = now + window_seconds

            retry_after = 0.0
            active: list[deque[float]] = []
            for key in keys:
                events = self._events.setdefault(key, deque())
                while events and events[0] <= now - window_seconds:
                    events.popleft()
                active.append(events)
                if len(events) >= limit:
                    retry_after = max(retry_after, events[0] + window_seconds - now)

            if retry_after > 0:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(max(1, ceil(retry_after)))},
                )

            for events in active:
                events.append(now)


rate_limiter = RateLimiter()
