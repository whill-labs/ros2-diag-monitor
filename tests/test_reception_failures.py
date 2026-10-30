from types import SimpleNamespace
import sys

import pytest

from diag_monitor.app import DiagMonitorApp
from diag_monitor.log_writer import LogWriter
from diag_monitor.ros_bridge import RosBridge
from diag_monitor.store import DiagStore


def message(level):
    return SimpleNamespace(status=[SimpleNamespace(
        name="sensor", level=level, message="State", hardware_id="sensor", values=[])])


@pytest.mark.parametrize("operation", ["write", "flush"])
def test_log_failure_keeps_receiving_diagnostics(tmp_path, monkeypatch, operation):
    writer = LogWriter(tmp_path / "diagnostics.jsonl")

    def fail(*args):
        raise OSError("No space left on device")

    monkeypatch.setattr(writer._file, operation, fail)
    store = DiagStore()
    bridge = RosBridge(store, "/diagnostics", writer)
    bridge._on_diagnostics(message(0))
    bridge._on_diagnostics(message(2))
    assert store.snapshot()[0]["sensor"].level == 2
    assert "No space" in bridge.logging_error
    writer.close()


def test_open_failure_is_reported_without_stopping_reception(monkeypatch, tmp_path):
    def fail(*args):
        raise PermissionError("Permission denied")
    monkeypatch.setattr("builtins.open", fail)
    writer = LogWriter(tmp_path / "diagnostics.jsonl")
    bridge = RosBridge(DiagStore(), "/diagnostics", writer)
    bridge._on_diagnostics(message(2))
    assert "Permission denied" in bridge.logging_error
    writer.close()


def test_failure_does_not_drop_later_array_items_or_retry_output(tmp_path, monkeypatch):
    writer = LogWriter(tmp_path / "diagnostics.jsonl")
    writes = []
    def fail(*args):
        writes.append(args)
        raise OSError("Disk full")
    monkeypatch.setattr(writer._file, "write", fail)
    store = DiagStore()
    bridge = RosBridge(store, "/diagnostics", writer)
    msg = message(0)
    other = message(2).status[0]
    other.name = "other"
    msg.status.append(other)
    bridge._on_diagnostics(msg)
    assert len(store.snapshot()[0]) == 2
    assert store.snapshot()[0]["other"].level == 2
    assert len(writes) == 1
    writer.close()


def test_close_failure_does_not_raise(tmp_path, monkeypatch):
    writer = LogWriter(tmp_path / "diagnostics.jsonl")
    def fail():
        raise OSError("Output unavailable")
    monkeypatch.setattr(writer._file, "close", fail)
    writer.close()
    assert writer.error == "Output unavailable"


@pytest.mark.parametrize("raises", [True, False])
def test_receiver_failure_is_exposed_to_ui(monkeypatch, raises):
    def spin(node):
        if raises:
            raise RuntimeError("Receive failure")
    monkeypatch.setitem(sys.modules, "rclpy", SimpleNamespace(spin=spin))
    bridge = RosBridge(DiagStore(), "/diagnostics")
    bridge._spin()
    assert bridge.receiver_error is not None


def test_expected_shutdown_does_not_report_receiver_failure(monkeypatch):
    def spin(node):
        raise RuntimeError("Context shutting down")
    monkeypatch.setitem(sys.modules, "rclpy", SimpleNamespace(spin=spin))
    bridge = RosBridge(DiagStore(), "/diagnostics")
    bridge._stopping = True
    bridge._spin()
    assert bridge.receiver_error is None


@pytest.mark.parametrize("failure, text, color, level", [
    ("logging_error", "Logging failed", "level-warn", 0),
    ("logging_error", "Logging failed", "level-error", 2),
    ("receiver_error", "Receiver stopped", "level-error", 0),
])
async def test_failures_remain_visible_instead_of_green(failure, text, color, level):
    store = DiagStore()
    store.update("sensor", level, "State", "sensor", [])
    bridge = SimpleNamespace(topic="/diagnostics", **{failure: "Unavailable [/]"})
    app = DiagMonitorApp(store, ros_bridge=bridge)
    async with app.run_test() as pilot:
        for _ in range(2):
            app._refresh_ui()
            await pilot.pause()
            header = app.query_one("#header")
            assert text in str(header.visual)
            assert "Unavailable [/]" in str(header.visual)
            assert header.has_class(color)
