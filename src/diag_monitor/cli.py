from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="diag-monitor",
        description="Terminal UI for monitoring ROS2 diagnostics",
    )
    parser.add_argument(
        "--topic",
        default="/diagnostics_agg",
        help="Diagnostics topic to subscribe (default: /diagnostics_agg)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Write status changes to JSONL file",
    )
    args = parser.parse_args()

    try:
        import rclpy  # noqa: F401
    except ImportError:
        print(
            "Error: rclpy is not available.\n"
            "Make sure ROS2 is installed and the environment is sourced:\n"
            "  source /opt/ros/<distro>/setup.bash",
            file=sys.stderr,
        )
        sys.exit(1)

    from diag_monitor.store import DiagStore
    from diag_monitor.log_writer import LogWriter
    from diag_monitor.ros_bridge import RosBridge
    from diag_monitor.app import DiagMonitorApp

    store = DiagStore()
    log_writer = LogWriter(args.log_file) if args.log_file else None
    bridge = RosBridge(store, args.topic, log_writer)

    bridge.start()
    try:
        app = DiagMonitorApp(store=store, ros_bridge=bridge)
        app.run()
    finally:
        bridge.shutdown()
        if log_writer is not None:
            log_writer.close()


if __name__ == "__main__":
    main()
