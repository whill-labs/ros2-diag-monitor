# AGENTS.md

This file provides guidance to coding agents working in this repository.

## Project Overview

`ros2-diag-monitor` is a ROS2 diagnostics monitor with a Textual-based terminal UI (a lazygit-style three-pane layout). It subscribes to `/diagnostics` or `/diagnostics_agg`, groups items by severity level, and shows details and status-change history for the selected item.

This is a regular Python package, not a ROS2/colcon package.

## Build & Development

Use `uv` for environment setup, dependency management, command execution, and tests in this repository. Prefer `uv sync`, `uv run ...`, and `uv run pytest` over calling `pip`, `python`, or `pytest` directly.

```bash
# Setup (requires a sourced ROS2 environment so rclpy is importable)
source /opt/ros/<distro>/setup.bash
uv venv --python 3.12 --system-site-packages
uv sync

# Run
uv run diag-monitor

# Run tests (all 9 tests, no ROS2 environment needed)
uv run pytest

# Run a single test
uv run pytest tests/test_store.py::test_store_update_level_change_records_history -v

# Build wheel
uv build
```

`rclpy` is a system dependency provided by ROS2, so it is not listed in `pyproject.toml`. The `--system-site-packages` flag is required for the virtual environment to access it.

## Architecture

```
CLI (`cli.py`) → orchestrates startup and shutdown
  ├── RosBridge (`ros_bridge.py`) — daemon thread running `rclpy.spin()`
  │     subscribes to `DiagnosticArray` and calls `store.update()`
  ├── DiagStore (`store.py`) — thread-safe state protected by `Lock`
  │     `DiagItem` (current status), `StatusChange` (level transitions)
  │     history: `deque(maxlen=100)` per item
  ├── DiagMonitorApp (`app.py`) — Textual app, reads snapshots every 1.0s
  │     ├── ItemList (`widgets/item_list.py`) — tree widget grouped by level
  │     ├── DetailView (`widgets/detail_view.py`) — selected item key-values
  │     └── HistoryView (`widgets/history_view.py`) — status-change log
  └── LogWriter (`log_writer.py`) — optional JSONL output
```

**Threading model:** `RosBridge` runs `rclpy.spin()` in a daemon thread. The Textual UI runs in the main thread and reads `store.snapshot()` every second. All store mutations are protected by a `Lock`.

**Level constants:** `store.py` defines `LEVEL_OK=0`, `LEVEL_WARN=1`, `LEVEL_ERROR=2`, and `LEVEL_STALE=3`.

## Testing

Tests mock `rclpy`, so no ROS2 environment is required to run them. `pytest` is configured in `pyproject.toml` to disable ROS2/ament pytest plugins (`-p no:launch_testing`, etc.), which keeps test runs clean outside colcon workspaces.

## Design Notes

- **History recording rule:** Only level transitions are recorded (for example, `OK → WARN`). Repeated updates at the same level are not stored. The first observation is also recorded (`prev_level=None`).
- **`rclpy` level type caveat:** `status.level` may be `int` or `bytes` depending on the ROS2 version. `ros_bridge.py`'s `_parse_level()` handles both.
- **JSONL log format:** `{"timestamp":"...","name":"...","prev":"OK","new":"WARN","message":"..."}` (`prev` is `null` on the first observation).
- **Default topic behavior:** `diag-monitor` starts on `/diagnostics_agg` by default, and the UI can switch topics with `t`.
- **Out of scope (future candidates):** diagnostic_aggregator config display, manual clear/reset, multi-topic subscription, web UI.
