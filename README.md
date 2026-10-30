# ros2-diag-monitor

A terminal UI for monitoring ROS2 diagnostics over SSH.

![screenshot](docs/assets/screenshot.png)

## Features

- Real-time diagnostics monitoring with lazygit-style 3-pane layout
- Header color changes based on worst diagnostic level (green=OK, yellow=WARN, red=ERROR)
- Items grouped by level (ERROR / WARN / STALE / OK)
- Detailed view with key-value pairs
- Status change history tracking
- Optional JSONL log file output
- Cause-change history with full diagnostic fields, plus current-state JSON snapshots
- Topic switching between `/diagnostics` and `/diagnostics_agg`
- Reload subscription with `R` key (useful after network recovery)
- Incremental name filter with `/` key (case-insensitive substring match)
- Keybinding help modal with `?` key

## Requirements

- Python >= 3.10 (must match your ROS2 distribution's Python)
- ROS2 environment with `rclpy` available

## Install

This tool requires access to system-installed `rclpy`, so it needs `--system-site-packages`.

```bash
source /opt/ros/jazzy/setup.bash

# Recommended: pipx with system site-packages
pipx install --system-site-packages ros2-diag-monitor
```

> **Note:** `uv tool install` does not support `--system-site-packages` and cannot be used.

## Usage

```bash
source /opt/ros/jazzy/setup.bash

# Monitor aggregated diagnostics (default)
diag-monitor

# Monitor /diagnostics
diag-monitor --topic /diagnostics

# Save status changes to file
diag-monitor --log-file diag.log

# Choose the output file for the e key
diag-monitor --snapshot-file /tmp/diagnostics.json

# Track a producer-specific cause field instead of the default cause fields
diag-monitor --history-key fault_code
```

History and JSONL record the first observation and changes in level, message,
hardware ID, or cause fields (`status`, `state`, `reason`, `error`, `error_code`).
The details pane shows the latest received report; history preserves event-time
snapshots under `History (state / cause changes)`.
Changes only in untracked fields, such as numeric frequency/time values, do not create events. Message changes always create events. Repeat `--history-key`
to choose a different set of cause fields. Each event preserves the hardware ID
and the full ordered `values` array as `{key, value}` pairs, including duplicate
keys and the measurements at the time of the event. Existing JSONL fields remain
available; the additional fields are additive.

Press `e` to export all observed diagnostics, independently of the name filter.
The JSON snapshot includes tool version, topic, export/observation timestamps,
levels and complete fields. It records the current state rather than waiting
for a new event. Export replaces the destination atomically; a failed export
leaves the previous snapshot intact and reports the error in the UI.
`reported_level` preserves a prior publisher level when the store supplies a
locally derived status; otherwise it is null and `level` is the reported level.

## Key Bindings

| Key | Action |
|---|---|
| `j`/`k` or `Up`/`Down` | Navigate items |
| `Tab` | Switch pane focus |
| `e` | Export the current diagnostic snapshot |
| `t` | Toggle topic (`/diagnostics` <-> `/diagnostics_agg`) |
| `R` | Reload (re-subscribe and clear) |
| `/` | Filter by name |
| `q` | Quit |
| `?` | Help |

## Development

```bash
git clone https://github.com/whill-labs/ros2-diag-monitor.git
cd ros2-diag-monitor

# Create venv with the same Python version as ROS2 and system-site-packages enabled
source /opt/ros/jazzy/setup.bash
uv venv --python 3.12 --system-site-packages
uv sync

# Run tests
uv run pytest

# Run in development
uv run diag-monitor
```

## License

MIT License

(C) 2026 WHILL Inc.

