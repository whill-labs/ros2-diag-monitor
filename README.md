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
- Topic switching between `/diagnostics` and `/diagnostics_agg`
- Reload subscription with `R` key (useful after network recovery)
- Incremental name filter with `/` key (case-insensitive substring match)
- Keybinding help modal with `?` key

## Requirements

- Python >= 3.10 (must match your ROS2 distribution's Python)
- ROS2 environment with `rclpy` available
- Textual >= 0.57 for terminal clipboard support

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
```

## Key Bindings

| Key | Action |
|---|---|
| `j`/`k` or `Up`/`Down` | Navigate items |
| `Tab` | Switch pane focus |
| `PageUp`/`PageDown`, `Home`/`End` | Scroll the focused details or history pane |
| `c` | Copy the entire selected diagnostic, including fields outside the viewport |
| `t` | Toggle topic (`/diagnostics` <-> `/diagnostics_agg`) |
| `R` | Reload (re-subscribe and clear) |
| `/` | Filter by name |
| `q` | Quit |
| `?` | Help |

Details and history scroll independently, including in an 80×24 SSH terminal.
Changing the selection returns both panes to the top; periodic updates preserve
the scroll position. Clipboard transfer uses the terminal's clipboard support
(OSC 52), which may need enabling in your SSH client or terminal multiplexer.

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

