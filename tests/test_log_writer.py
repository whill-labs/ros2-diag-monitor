import json
from datetime import datetime
from pathlib import Path

from diag_monitor.log_writer import LogWriter
from diag_monitor.store import StatusChange, LEVEL_OK, LEVEL_WARN


def test_log_writer_writes_jsonl(tmp_path: Path):
    log_file = tmp_path / "diag.log"
    writer = LogWriter(log_file)

    change = StatusChange(
        timestamp=datetime(2026, 4, 8, 12, 3, 1),
        prev_level=LEVEL_OK,
        new_level=LEVEL_WARN,
        message="Frequency too low",
    )
    writer.write("topic_monitor: lidar_freq", change)
    writer.close()

    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["name"] == "topic_monitor: lidar_freq"
    assert record["prev"] == "OK"
    assert record["new"] == "WARN"
    assert record["message"] == "Frequency too low"
    assert "timestamp" in record


def test_log_writer_first_seen(tmp_path: Path):
    log_file = tmp_path / "diag.log"
    writer = LogWriter(log_file)

    change = StatusChange(
        timestamp=datetime(2026, 4, 8, 12, 0, 0),
        prev_level=None,
        new_level=LEVEL_OK,
        message="OK",
    )
    writer.write("sensor: freq", change)
    writer.close()

    record = json.loads(log_file.read_text().strip())
    assert record["prev"] is None
    assert record["new"] == "OK"
