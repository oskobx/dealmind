"""Append-only events.jsonl writer (§11 safety net). One JSON object per line, never the API key."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path


class EventLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.listeners: list[Callable[[dict], None]] = []
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, kind: str, **data: object) -> dict:
        event = {"t": round(time.time(), 3), "kind": kind, **data}
        line = json.dumps(event, default=str)
        with self._lock:
            if self.path is not None:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            for listener in list(self.listeners):
                listener(event)
        return event


_current = EventLog()


def set_current(log: EventLog) -> None:
    global _current
    _current = log


def current() -> EventLog:
    return _current


def emit(kind: str, **data: object) -> dict:
    """Write one event to the current log (a no-op sink until run.py sets a file)."""
    return _current.emit(kind, **data)
