from queue import Empty, Full, Queue
from threading import Lock
from typing import Any

_subscribers: set[Queue[dict[str, Any]]] = set()
_lock = Lock()


def subscribe() -> Queue[dict[str, Any]]:
    subscriber: Queue[dict[str, Any]] = Queue(maxsize=100)
    with _lock:
        _subscribers.add(subscriber)
    return subscriber


def unsubscribe(subscriber: Queue[dict[str, Any]]) -> None:
    with _lock:
        _subscribers.discard(subscriber)


def publish_check(check: dict[str, Any]) -> None:
    with _lock:
        subscribers = tuple(_subscribers)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(check)
        except Full:
            try:
                subscriber.get_nowait()
            except Empty:
                pass
            try:
                subscriber.put_nowait(check)
            except Full:
                pass
