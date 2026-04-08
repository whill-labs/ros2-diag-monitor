from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diag_monitor.log_writer import LogWriter
    from diag_monitor.store import DiagStore


def _parse_level(level: int | bytes) -> int:
    """Convert DiagnosticStatus.level to int. ROS2 may return bytes (e.g. b'\\x00')."""
    if isinstance(level, int):
        return level
    return level[0]


class RosBridge:
    def __init__(self, store: DiagStore, topic: str, log_writer: LogWriter | None = None) -> None:
        self._store = store
        self._topic = topic
        self._log_writer = log_writer
        self._thread: threading.Thread | None = None
        self._node = None

    def start(self) -> None:
        import rclpy
        from rclpy.node import Node
        from diagnostic_msgs.msg import DiagnosticArray

        if not rclpy.ok():
            rclpy.init()
        self._node = Node("diag_monitor")
        self._node.create_subscription(
            DiagnosticArray,
            self._topic,
            self._on_diagnostics,
            10,
        )
        self._thread = threading.Thread(target=rclpy.spin, args=(self._node,), daemon=True)
        self._thread.start()

    def _on_diagnostics(self, msg) -> None:
        from diagnostic_msgs.msg import DiagnosticArray

        for status in msg.status:
            values = [(kv.key, kv.value) for kv in status.values]
            change = self._store.update(
                name=status.name,
                level=_parse_level(status.level),
                message=status.message,
                hardware_id=status.hardware_id,
                values=values,
            )
            if change is not None and self._log_writer is not None:
                self._log_writer.write(status.name, change)

    def switch_topic(self, new_topic: str) -> None:
        if self._node is None:
            return
        from diagnostic_msgs.msg import DiagnosticArray

        for sub in self._node.subscriptions:
            self._node.destroy_subscription(sub)

        self._topic = new_topic
        self._node.create_subscription(
            DiagnosticArray,
            self._topic,
            self._on_diagnostics,
            10,
        )
        self._store.clear()

    def reload(self) -> None:
        """Re-create subscription and clear the store."""
        self.switch_topic(self._topic)

    @property
    def topic(self) -> str:
        return self._topic

    def shutdown(self) -> None:
        import rclpy

        # Stop rclpy first so spin() returns
        rclpy.try_shutdown()
        # Wait for spin thread to finish
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        # Destroy node
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
