import sys
from types import SimpleNamespace

import pytest

from diag_monitor.cli import main


def test_cli_wires_history_and_export_options_and_shuts_down(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "rclpy", SimpleNamespace())
    path = tmp_path / "snapshot.json"
    monkeypatch.setattr(sys, "argv", ["diag-monitor", "--topic", "/diagnostics",
                                    "--history-key", "fault", "--snapshot-file", str(path)])
    class Bridge:
        def __init__(self, store, topic, writer):
            assert topic == "/diagnostics"
            assert store._history_keys == {"fault"}
        def start(self):
            calls.append("start")
        def shutdown(self):
            calls.append("shutdown")
    class App:
        def __init__(self, store, ros_bridge, snapshot_file):
            assert snapshot_file == path
        def run(self):
            calls.append("run")
    monkeypatch.setattr("diag_monitor.ros_bridge.RosBridge", Bridge)
    monkeypatch.setattr("diag_monitor.app.DiagMonitorApp", App)
    main()
    assert calls == ["start", "run", "shutdown"]


def test_cli_reports_missing_ros_environment(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["diag-monitor"])
    monkeypatch.setitem(sys.modules, "rclpy", None)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "rclpy is not available" in capsys.readouterr().err
