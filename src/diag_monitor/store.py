from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

LEVEL_OK = 0
LEVEL_WARN = 1
LEVEL_ERROR = 2
LEVEL_STALE = 3

LEVEL_NAMES = {LEVEL_OK: "OK", LEVEL_WARN: "WARN", LEVEL_ERROR: "ERROR", LEVEL_STALE: "STALE"}


@dataclass
class DiagItem:
    name: str
    level: int
    message: str
    hardware_id: str
    values: list[tuple[str, str]]
    last_updated: datetime


@dataclass
class StatusChange:
    timestamp: datetime
    prev_level: int | None
    new_level: int
    message: str


_HISTORY_MAXLEN = 100


class DiagStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, DiagItem] = {}
        self._history: dict[str, deque[StatusChange]] = {}
        self._last_msg_time: datetime | None = None

    def update(
        self,
        name: str,
        level: int,
        message: str,
        hardware_id: str,
        values: list[tuple[str, str]],
    ) -> StatusChange | None:
        now = datetime.now()
        with self._lock:
            self._last_msg_time = now
            prev = self._items.get(name)
            self._items[name] = DiagItem(
                name=name,
                level=level,
                message=message,
                hardware_id=hardware_id,
                values=values,
                last_updated=now,
            )

            if name not in self._history:
                self._history[name] = deque(maxlen=_HISTORY_MAXLEN)

            if prev is None:
                change = StatusChange(timestamp=now, prev_level=None, new_level=level, message=message)
                self._history[name].append(change)
                return change

            if prev.level != level:
                change = StatusChange(timestamp=now, prev_level=prev.level, new_level=level, message=message)
                self._history[name].append(change)
                return change

            return None

    def snapshot(self) -> tuple[dict[str, DiagItem], dict[str, list[StatusChange]]]:
        with self._lock:
            items = dict(self._items)
            history = {k: list(v) for k, v in self._history.items()}
            return items, history

    @property
    def last_msg_time(self) -> datetime | None:
        with self._lock:
            return self._last_msg_time

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._history.clear()
            self._last_msg_time = None
