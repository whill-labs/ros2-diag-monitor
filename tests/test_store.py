from datetime import datetime
from diag_monitor.store import DiagItem, StatusChange, DiagStore, LEVEL_OK, LEVEL_WARN


def test_diag_item_creation():
    item = DiagItem(
        name="ekf: frequency",
        level=0,
        message="OK",
        hardware_id="ekf_node",
        values=[("actual_freq", "10.0"), ("min_freq", "9.0")],
        last_updated=datetime(2026, 4, 8, 12, 0, 0),
    )
    assert item.name == "ekf: frequency"
    assert item.level == 0
    assert len(item.values) == 2


def test_status_change_first_seen():
    change = StatusChange(
        timestamp=datetime(2026, 4, 8, 12, 0, 0),
        prev_level=None,
        new_level=0,
        message="OK",
    )
    assert change.prev_level is None
    assert change.new_level == 0


def test_store_update_new_item():
    store = DiagStore()
    store.update("sensor: freq", LEVEL_OK, "OK", "sensor_node", [("hz", "10")])

    items, history = store.snapshot()
    assert "sensor: freq" in items
    assert items["sensor: freq"].level == LEVEL_OK

    changes = history["sensor: freq"]
    assert len(changes) == 1
    assert changes[0].prev_level is None
    assert changes[0].new_level == LEVEL_OK


def test_store_update_level_change_records_history():
    store = DiagStore()
    store.update("sensor: freq", LEVEL_OK, "OK", "sensor_node", [])
    store.update("sensor: freq", LEVEL_WARN, "Low freq", "sensor_node", [])

    _, history = store.snapshot()
    changes = history["sensor: freq"]
    assert len(changes) == 2
    assert changes[1].prev_level == LEVEL_OK
    assert changes[1].new_level == LEVEL_WARN


def test_store_update_same_level_no_new_history():
    store = DiagStore()
    store.update("sensor: freq", LEVEL_OK, "OK", "sensor_node", [])
    store.update("sensor: freq", LEVEL_OK, "Still OK", "sensor_node", [])

    _, history = store.snapshot()
    changes = history["sensor: freq"]
    assert len(changes) == 1  # Only first-seen; same level does not add history
