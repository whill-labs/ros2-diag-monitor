from __future__ import annotations

import json
from pathlib import Path
from typing import IO

from diag_monitor.store import StatusChange, LEVEL_NAMES


class LogWriter:
    def __init__(self, path: Path) -> None:
        self._file: IO[str] = open(path, "a")

    def write(self, name: str, change: StatusChange) -> None:
        record = {
            "timestamp": change.timestamp.isoformat(timespec="seconds"),
            "name": name,
            "prev": LEVEL_NAMES.get(change.prev_level) if change.prev_level is not None else None,
            "new": LEVEL_NAMES[change.new_level],
            "message": change.message,
        }
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
