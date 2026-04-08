from diag_monitor.ros_bridge import _parse_level


def test_parse_level_int():
    assert _parse_level(0) == 0
    assert _parse_level(1) == 1
    assert _parse_level(2) == 2
    assert _parse_level(3) == 3


def test_parse_level_bytes():
    """ROS2 Jazzy returns DiagnosticStatus.level as bytes."""
    assert _parse_level(b"\x00") == 0
    assert _parse_level(b"\x01") == 1
    assert _parse_level(b"\x02") == 2
    assert _parse_level(b"\x03") == 3
