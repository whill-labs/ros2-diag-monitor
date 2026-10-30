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
    hardware_id: str = ""
    values: list[tuple[str, str]] = field(default_factory=list)


_HISTORY_MAXLEN = 100
DEFAULT_HISTORY_KEYS = ("status", "state", "reason", "error", "error_code")


class DiagStore:
    def __init__(self, history_keys: list[str] | None = None) -> None:
        self._lock = Lock()
        self._items: dict[str, DiagItem] = {}
        self._history: dict[str, deque[StatusChange]] = {}
        self._last_msg_time: datetime | None = None
        self._history_keys = frozenset(DEFAULT_HISTORY_KEYS if history_keys is None else history_keys)

    def _cause(self, values: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return sorted((key, value) for key, value in values if key in self._history_keys)

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
                values=list(values),
                last_updated=now,
            )

            if name not in self._history:
                self._history[name] = deque(maxlen=_HISTORY_MAXLEN)

            if (prev is None or prev.level != level or prev.message != message
                    or prev.hardware_id != hardware_id or self._cause(prev.values) != self._cause(values)):
                change = StatusChange(timestamp=now, prev_level=prev.level if prev else None,
                                      new_level=level, message=message, hardware_id=hardware_id,
                                      values=list(values))
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
