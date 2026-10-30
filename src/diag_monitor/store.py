from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime
from threading import Lock
from time import monotonic

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
    received_at: float = field(default_factory=monotonic)
    reported_level: int | None = None


@dataclass
class StatusChange:
    timestamp: datetime
    prev_level: int | None
    new_level: int
    message: str


_HISTORY_MAXLEN = 100


class DiagStore:
    def __init__(self, stale_after: float = 3.0) -> None:
        self._lock = Lock()
        self._items: dict[str, DiagItem] = {}
        self._history: dict[str, deque[StatusChange]] = {}
        self._last_msg_time: datetime | None = None
        self._last_received: float | None = None
        self.stale_after = stale_after

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
            received_at = monotonic()
            self._last_msg_time = now
            self._last_received = received_at
            prev = self._items.get(name)
            self._items[name] = DiagItem(
                name=name,
                level=level,
                message=message,
                hardware_id=hardware_id,
                values=values,
                last_updated=now,
                received_at=received_at,
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
            now = monotonic()
            items = {
                name: replace(item, level=LEVEL_STALE, reported_level=item.level)
                if self.stale_after > 0 and now - item.received_at >= self.stale_after
                else item
                for name, item in self._items.items()
            }
            history = {k: list(v) for k, v in self._history.items()}
            return items, history

    @property
    def last_msg_time(self) -> datetime | None:
        with self._lock:
            return self._last_msg_time

    @property
    def last_received(self) -> float | None:
        with self._lock:
            return self._last_received

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._history.clear()
            self._last_msg_time = None
            self._last_received = None
