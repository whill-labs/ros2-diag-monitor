#!/usr/bin/env python3
"""Fake diagnostic publisher for testing diag-monitor."""

from __future__ import annotations

import argparse
import random
import time

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# ---------------------------------------------------------------------------
# Predefined realistic diagnostic items
# ---------------------------------------------------------------------------

_ITEMS = [
    {
        "name": "sensor/lidar: frequency",
        "hardware_id": "lidar_driver",
        "values": [("actual_freq", "10.0"), ("min_freq", "9.0")],
        "warn_values": [("actual_freq", "7.5"), ("min_freq", "9.0")],
        "error_values": [("actual_freq", "2.1"), ("min_freq", "9.0")],
        "warn_msg": "Frequency too low",
        "error_msg": "Frequency critically low",
    },
    {
        "name": "sensor/imu: frequency",
        "hardware_id": "imu_driver",
        "values": [("actual_freq", "100.0"), ("min_freq", "95.0")],
        "warn_values": [("actual_freq", "80.0"), ("min_freq", "95.0")],
        "error_values": [("actual_freq", "30.0"), ("min_freq", "95.0")],
        "warn_msg": "Frequency below threshold",
        "error_msg": "Frequency critically low",
    },
    {
        "name": "sensor/camera: connection",
        "hardware_id": "camera_driver",
        "values": [("status", "connected"), ("fps", "30")],
        "warn_values": [("status", "unstable"), ("fps", "15")],
        "error_values": [("status", "disconnected"), ("fps", "0")],
        "warn_msg": "Connection unstable",
        "error_msg": "Connection lost",
    },
    {
        "name": "motor/left: temperature",
        "hardware_id": "motor_controller",
        "values": [("temperature", "45.2"), ("threshold", "80.0")],
        "warn_values": [("temperature", "72.5"), ("threshold", "80.0")],
        "error_values": [("temperature", "88.3"), ("threshold", "80.0")],
        "warn_msg": "Temperature approaching limit",
        "error_msg": "Overheating",
    },
    {
        "name": "motor/right: temperature",
        "hardware_id": "motor_controller",
        "values": [("temperature", "44.8"), ("threshold", "80.0")],
        "warn_values": [("temperature", "71.0"), ("threshold", "80.0")],
        "error_values": [("temperature", "85.9"), ("threshold", "80.0")],
        "warn_msg": "Temperature approaching limit",
        "error_msg": "Overheating",
    },
    {
        "name": "battery: voltage",
        "hardware_id": "bms",
        "values": [("voltage", "25.2"), ("percentage", "85")],
        "warn_values": [("voltage", "22.1"), ("percentage", "25")],
        "error_values": [("voltage", "19.8"), ("percentage", "8")],
        "warn_msg": "Low battery",
        "error_msg": "Battery critical",
    },
    {
        "name": "ekf: frequency",
        "hardware_id": "ekf_node",
        "values": [("actual_freq", "50.0"), ("min_freq", "45.0")],
        "warn_values": [("actual_freq", "35.0"), ("min_freq", "45.0")],
        "error_values": [("actual_freq", "10.0"), ("min_freq", "45.0")],
        "warn_msg": "EKF running slow",
        "error_msg": "EKF severely degraded",
    },
    {
        "name": "network: latency",
        "hardware_id": "network_monitor",
        "values": [("latency_ms", "12"), ("packet_loss", "0.0")],
        "warn_values": [("latency_ms", "150"), ("packet_loss", "2.5")],
        "error_values": [("latency_ms", "800"), ("packet_loss", "15.0")],
        "warn_msg": "High latency",
        "error_msg": "Network degraded",
    },
    {
        "name": "disk: usage",
        "hardware_id": "system_monitor",
        "values": [("usage_percent", "42"), ("free_gb", "58.3")],
        "warn_values": [("usage_percent", "82"), ("free_gb", "18.1")],
        "error_values": [("usage_percent", "96"), ("free_gb", "4.2")],
        "warn_msg": "Disk usage high",
        "error_msg": "Disk nearly full",
    },
    {
        "name": "cpu: temperature",
        "hardware_id": "system_monitor",
        "values": [("temperature", "52.0"), ("max_temp", "90.0")],
        "warn_values": [("temperature", "78.0"), ("max_temp", "90.0")],
        "error_values": [("temperature", "92.5"), ("max_temp", "90.0")],
        "warn_msg": "CPU temperature high",
        "error_msg": "CPU overheating",
    },
]

LEVEL_OK = DiagnosticStatus.OK
LEVEL_WARN = DiagnosticStatus.WARN
LEVEL_ERROR = DiagnosticStatus.ERROR
LEVEL_STALE = DiagnosticStatus.STALE

_LEVEL_MAP = {"ok": LEVEL_OK, "warn": LEVEL_WARN, "error": LEVEL_ERROR, "stale": LEVEL_STALE}

# ---------------------------------------------------------------------------
# Scenario definition (timestamps in seconds within a ~90s cycle)
# ---------------------------------------------------------------------------

_SCENARIO = [
    # (time, item_name, level)
    (20, "battery: voltage", LEVEL_WARN),
    (40, "sensor/lidar: frequency", LEVEL_ERROR),
    (60, "sensor/lidar: frequency", LEVEL_OK),
    (70, "battery: voltage", LEVEL_OK),
]

_SCENARIO_CYCLE = 90


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_items(num: int) -> list[dict]:
    """Return a list of item definitions, extending with extras if needed."""
    items = list(_ITEMS[:num])
    for i in range(len(items), num):
        items.append(
            {
                "name": f"extra/item_{i + 1}",
                "hardware_id": "extra",
                "values": [("value", "0")],
                "warn_values": [("value", "1")],
                "error_values": [("value", "2")],
                "warn_msg": "Warning",
                "error_msg": "Error",
            }
        )
    return items


def _make_status(item: dict, level: int) -> DiagnosticStatus:
    """Create a DiagnosticStatus message for an item at the given level."""
    status = DiagnosticStatus()
    status.name = item["name"]
    status.hardware_id = item["hardware_id"]
    status.level = level

    if level == LEVEL_OK:
        status.message = "OK"
        values = item["values"]
    elif level == LEVEL_WARN:
        status.message = item.get("warn_msg", "Warning")
        values = item.get("warn_values", item["values"])
    elif level == LEVEL_ERROR:
        status.message = item.get("error_msg", "Error")
        values = item.get("error_values", item["values"])
    else:  # STALE
        status.message = "Stale"
        values = item["values"]

    status.values = [KeyValue(key=k, value=v) for k, v in values]
    return status


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------


class FakeDiagPublisher(Node):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__("fake_diag_publisher")
        self._pub = self.create_publisher(DiagnosticArray, args.topic, 10)
        self._items = _build_items(args.num_items)
        self._mode = args.mode
        self._fixed_level = _LEVEL_MAP[args.level]
        self._rate = args.rate
        self._start_time = time.monotonic()

        # Per-item current levels (for scenario and random modes)
        self._levels: dict[str, int] = {item["name"]: LEVEL_OK for item in self._items}

        period = 1.0 / self._rate
        self.create_timer(period, self._publish)
        self.get_logger().info(
            f"Publishing {len(self._items)} items on '{args.topic}' "
            f"at {self._rate} Hz (mode: {self._mode})"
        )

    def _publish(self) -> None:
        if self._mode == "scenario":
            self._update_scenario()
        elif self._mode == "random":
            self._update_random()
        # fixed mode: levels are set once and never change

        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        for item in self._items:
            level = self._fixed_level if self._mode == "fixed" else self._levels[item["name"]]
            msg.status.append(_make_status(item, level))
        self._pub.publish(msg)

    def _update_scenario(self) -> None:
        elapsed = (time.monotonic() - self._start_time) % _SCENARIO_CYCLE
        # Reset all to OK, then apply scenario events that have occurred
        for item in self._items:
            self._levels[item["name"]] = LEVEL_OK
        for t, name, level in _SCENARIO:
            if elapsed >= t and name in self._levels:
                self._levels[name] = level

    def _update_random(self) -> None:
        for item in self._items:
            if random.random() < 0.05:
                self._levels[item["name"]] = random.choice([LEVEL_OK, LEVEL_WARN, LEVEL_ERROR])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake diagnostic publisher for testing diag-monitor")
    parser.add_argument("--mode", choices=["scenario", "random", "fixed"], default="scenario")
    parser.add_argument("--rate", type=float, default=1.0, help="Publish rate in Hz")
    parser.add_argument("--num-items", type=int, default=10, help="Number of diagnostic items")
    parser.add_argument("--level", choices=["ok", "warn", "error", "stale"], default="ok",
                        help="Level for fixed mode")
    parser.add_argument("--topic", default="/diagnostics", help="Topic to publish on")
    args = parser.parse_args()

    rclpy.init()
    node = FakeDiagPublisher(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
