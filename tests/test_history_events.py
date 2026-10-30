import json

import pytest

from diag_monitor.app import DiagMonitorApp
from diag_monitor.export import export_snapshot
from diag_monitor.log_writer import LogWriter
from diag_monitor.store import DiagStore


def test_actual_topic_causes_and_recovery_keep_event_evidence(tmp_path):
    store = DiagStore()
    path = tmp_path / "events.jsonl"
    writer = LogWriter(path)
    for index, cause in enumerate(("NotReceived", "ErrorRate", "Timeout", "OK")):
        level = 0 if cause == "OK" else 2
        fields = [("status", cause), ("measured_rate", str(index)), ("rate", "5 [Hz]"), ("rate", "2 [Hz]")]
        event = store.update("monitor", level, "OK" if level == 0 else "Error", "device", fields)
        assert event is not None
        writer.write("monitor", event)
        fields.clear()
    writer.close()
    events = store.snapshot()[1]["monitor"]
    assert [event.values[0][1] for event in events] == ["NotReceived", "ErrorRate", "Timeout", "OK"]
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == 4
    assert all(record["hardware_id"] == "device" for record in records)
    assert records[0]["values"][-2:] == [{"key": "rate", "value": "5 [Hz]"},
                                        {"key": "rate", "value": "2 [Hz]"}]


def test_repeated_measurements_do_not_flood_history():
    store = DiagStore()
    for index in range(20):
        store.update("monitor", 2, "Error", "device",
                     [("measured_rate", str(index)), ("status", "Timeout"), ("now", str(index))])
    assert len(store.snapshot()[1]["monitor"]) == 1
    store.update("monitor", 2, "Disconnected", "device", [("status", "Timeout")])
    assert len(store.snapshot()[1]["monitor"]) == 2


def test_custom_cause_keys_and_duplicate_cause_fields():
    store = DiagStore(history_keys=["fault_code"])
    for code in ("A", "B"):
        store.update("sensor", 2, "Error", "device", [("fault_code", code), ("fault_code", "C")])
    store.update("sensor", 2, "Error", "device", [("fault_code", "C"), ("fault_code", "B")])
    assert len(store.snapshot()[1]["sensor"]) == 2


async def test_history_renders_initial_and_same_level_causes_literally():
    store = DiagStore()
    for cause in ("NotReceived", "Timeout"):
        store.update("sensor", 2, "Error", "device", [("status", cause), ("rate", "5 [Hz]")])
    app = DiagMonitorApp(store)
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()
        tree = app.query_one("#item-list")
        tree.move_cursor(tree._leaves["sensor"])
        await pilot.pause()
        app._refresh_ui()
        text = str(app.query_one("#history-view").visual)
        assert "History (state / cause changes)" in text
        assert "NotReceived" in text and "Timeout" in text
        assert "details changed" in text and "first seen" in text
        assert "5 [Hz]" in text


async def test_export_includes_unfiltered_current_statuses_and_duplicate_values(tmp_path):
    store = DiagStore()
    store.update("sensor", 2, "Error", "device", [("rate", "5 [Hz]"), ("rate", "2 [Hz]")])
    store.update("map", 0, "OK", "map", [])
    path = tmp_path / "snapshot.json"
    app = DiagMonitorApp(store, snapshot_file=path)
    async with app.run_test() as pilot:
        app._filter_text = "sensor"
        await pilot.press("e")
        record = json.loads(path.read_text())
        assert len(record["diagnostics"]) == 2
        assert record["topic"] == "/diagnostics"
        assert record["tool_version"] and record["created_at"]
        sensor = next(item for item in record["diagnostics"] if item["name"] == "sensor")
        assert len(sensor["values"]) == 2
        assert sensor["values"][0]["value"] == "5 [Hz]"
        await pilot.press("/")
        await pilot.press("e")
        assert app.query_one("#filter-input").value == "e"


def test_failed_export_preserves_previous_report_and_removes_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.json"
    path.write_text("previous report")
    def fail(*args, **kwargs):
        raise OSError("Disk full")
    monkeypatch.setattr("diag_monitor.export.json.dump", fail)
    with pytest.raises(OSError):
        export_snapshot(path, "/diagnostics", [])
    assert path.read_text() == "previous report"
    assert list(tmp_path.iterdir()) == [path]


async def test_export_failure_is_reported_without_closing_ui(tmp_path, monkeypatch):
    app = DiagMonitorApp(DiagStore(), snapshot_file=tmp_path / "missing" / "snapshot.json")
    notices = []
    monkeypatch.setattr(app, "notify", lambda text, **kwargs: notices.append((text, kwargs)))
    async with app.run_test() as pilot:
        await pilot.press("e")
        assert "Snapshot export failed" in notices[0][0]
        assert notices[0][1]["severity"] == "error"


async def test_export_path_with_markup_is_literal(tmp_path):
    directory = tmp_path / "sensor ["
    directory.mkdir()
    path = directory / "] report.json"
    app = DiagMonitorApp(DiagStore(), snapshot_file=path)
    async with app.run_test() as pilot:
        await pilot.press("e")
        await pilot.pause()
        assert path.exists()
