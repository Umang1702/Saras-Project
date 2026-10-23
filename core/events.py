"""
Minimal synchronous event bus, used sparingly (e.g. UI/tray updates,
scheduler-triggered routines) — intentionally simple rather than a full
pub/sub framework, per the "don't overengineer" directive.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable) -> None:
        self._subscribers[event_name].append(callback)

    def publish(self, event_name: str, **payload) -> None:
        for callback in self._subscribers.get(event_name, []):
            callback(**payload)
