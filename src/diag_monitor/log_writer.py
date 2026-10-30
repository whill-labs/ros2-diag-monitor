from __future__ import annotations

import json
from pathlib import Path
from typing import IO

from diag_monitor.store import StatusChange, LEVEL_NAMES


class LogWriter:
    def __init__(self, path: Path) -> None:
        self.error: str | None = None
        self._file: IO[str] | None = None
        try:
            self._file = open(path, "a")
        except OSError as exc:
            self.error = str(exc)

    def write(self, name: str, change: StatusChange) -> None:
        if self._file is None or self.error is not None:
            return
        record = {
            "timestamp": change.timestamp.isoformat(timespec="seconds"),
            "name": name,
            "prev": LEVEL_NAMES.get(change.prev_level) if change.prev_level is not None else None,
            "new": LEVEL_NAMES[change.new_level],
            "message": change.message,
        }
        try:
            self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._file.flush()
        except (OSError, UnicodeError) as exc:
            self.error = str(exc)

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            except OSError as exc:
                self.error = self.error or str(exc)
