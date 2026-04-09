# tools

Utility scripts for development and testing.

## fake_diag_publisher.py

A ROS2 node that publishes dummy `DiagnosticArray` messages to `/diagnostics` for testing `diag-monitor`.

```bash
source /opt/ros/jazzy/setup.bash

# Scenario mode (default) — levels change in a ~90s cycle
python tools/fake_diag_publisher.py

# Random mode — each item has a 5% chance of level change per cycle
python tools/fake_diag_publisher.py --mode random

# Fixed mode — all items at a specified level (useful for color verification)
python tools/fake_diag_publisher.py --mode fixed --level error

# Adjust item count, rate, and topic
python tools/fake_diag_publisher.py --num-items 50 --rate 2.0 --topic /diagnostics_agg
```

## test_color.py

A minimal Textual app to verify that background color changes work in your terminal. Cycles through green, yellow, and red every 3 seconds.

```bash
uv run python tools/test_color.py
```
