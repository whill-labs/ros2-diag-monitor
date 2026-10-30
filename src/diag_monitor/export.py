from datetime import datetime
import json
from pathlib import Path
import tempfile

from diag_monitor import __version__
from diag_monitor.store import DiagItem, LEVEL_NAMES


def export_snapshot(path: Path, topic: str, items: list[DiagItem]) -> None:
    """Atomically save every observed diagnostic, preserving ordered duplicate fields."""
    record = {
        "schema_version": 1,
        "tool_version": __version__,
        "created_at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "topic": topic,
        "diagnostics": [{
            "name": item.name, "hardware_id": item.hardware_id,
            "level": item.level, "level_name": LEVEL_NAMES.get(item.level, "UNKNOWN"),
            "reported_level": getattr(item, "reported_level", None),
            "message": item.message, "last_updated": item.last_updated.isoformat(),
            "values": [{"key": key, "value": value} for key, value in item.values],
        } for item in sorted(items, key=lambda item: (item.name, item.hardware_id))],
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
