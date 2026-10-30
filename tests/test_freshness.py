import pytest

from diag_monitor.app import DiagMonitorApp
from diag_monitor.cli import stale_timeout
from diag_monitor.store import DiagStore, LEVEL_OK, LEVEL_ERROR, LEVEL_STALE


@pytest.fixture
def clock(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("diag_monitor.store.monotonic", lambda: now[0])
    monkeypatch.setattr("diag_monitor.app.monotonic", lambda: now[0])
    return now


def test_silent_item_expires_independently_and_recovers(clock):
    store = DiagStore()
    store.update("lidar", LEVEL_ERROR, "Lost", "lidar", [("status", "Timeout")])
    clock[0] += 3
    store.update("map", LEVEL_OK, "OK", "map", [])
    items, history = store.snapshot()
    assert items["lidar"].level == LEVEL_STALE
    assert items["lidar"].reported_level == LEVEL_ERROR
    assert items["lidar"].values == [("status", "Timeout")]
    assert items["map"].level == LEVEL_OK
    assert len(history["lidar"]) == 1
    store.update("lidar", LEVEL_ERROR, "Lost", "lidar", [])
    assert store.snapshot()[0]["lidar"].level == LEVEL_ERROR
    assert store.snapshot()[0]["lidar"].reported_level is None


def test_expiry_needs_no_callback_and_does_not_change_source(clock):
    store = DiagStore()
    store.update("sensor", LEVEL_OK, "OK", "sensor", [])
    original = store.snapshot()[0]["sensor"]
    clock[0] += 3
    assert store.snapshot()[0]["sensor"].level == LEVEL_STALE
    assert original.level == LEVEL_OK
    assert original.last_updated == store.snapshot()[0]["sensor"].last_updated


def test_disabled_expiry_and_clear(clock):
    store = DiagStore(stale_after=0)
    store.update("sensor", LEVEL_OK, "OK", "sensor", [])
    clock[0] += 1000
    assert store.snapshot()[0]["sensor"].level == LEVEL_OK
    store.clear()
    assert store.snapshot() == ({}, {})
    assert store.last_received is None


@pytest.mark.parametrize("value", ["-1", "nan", "inf", "oops"])
def test_invalid_timeout(value):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):
        stale_timeout(value)


@pytest.mark.parametrize("level", [None, LEVEL_STALE])
async def test_unknown_state_never_has_green_header(clock, level):
    store = DiagStore()
    if level is not None:
        store.update("map", LEVEL_OK, "OK", "map", [])
        store.update("lidar", level, "Unknown", "lidar", [])
    app = DiagMonitorApp(store)
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()
        header = app.query_one("#header")
        assert not header.has_class("level-ok")
        assert ("Waiting for diagnostics" if level is None else "STALE 1") in str(header.visual)


async def test_persistent_stream_loss_and_recovery(clock):
    store = DiagStore()
    store.update("sensor", LEVEL_OK, "OK", "sensor", [])
    app = DiagMonitorApp(store)
    async with app.run_test() as pilot:
        clock[0] += 12
        app._refresh_ui()
        await pilot.pause()
        header = app.query_one("#header")
        assert "No data for 12s" in str(header.visual)
        assert header.has_class("level-stale")
        store.update("sensor", LEVEL_OK, "OK", "sensor", [])
        app._refresh_ui()
        await pilot.pause()
        assert header.has_class("level-ok")
        assert "No data" not in str(header.visual)


@pytest.mark.parametrize("levels, expected", [([LEVEL_STALE], "level-stale"),
                                            ([LEVEL_ERROR, LEVEL_STALE], "level-error")])
async def test_stale_never_hides_a_fresh_error(clock, levels, expected):
    store = DiagStore()
    for i, level in enumerate(levels):
        store.update(str(i), level, "Status", str(i), [])
    app = DiagMonitorApp(store)
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()
        assert app.query_one("#header").has_class(expected)


def test_wall_clock_changes_do_not_affect_expiry(clock, monkeypatch):
    from datetime import datetime
    from types import SimpleNamespace
    store = DiagStore()
    store.update("sensor", LEVEL_OK, "OK", "sensor", [])
    monkeypatch.setattr("diag_monitor.store.datetime",
                        SimpleNamespace(now=lambda: datetime(2000, 1, 1)))
    store.update("map", LEVEL_OK, "OK", "map", [])
    assert store.snapshot()[0]["sensor"].level == LEVEL_OK
    clock[0] += 3
    assert store.snapshot()[0]["sensor"].level == LEVEL_STALE


async def test_each_stream_outage_notifies_again_after_recovery(clock, monkeypatch):
    from types import SimpleNamespace
    store = DiagStore()
    store.update("sensor", LEVEL_OK, "OK", "sensor", [])
    app = DiagMonitorApp(store, ros_bridge=SimpleNamespace(topic="/diagnostics"))
    notices = []
    monkeypatch.setattr(app, "notify", lambda *args, **kwargs: notices.append(args[0]))
    async with app.run_test() as pilot:
        clock[0] += 11
        app._refresh_ui()
        store.update("sensor", LEVEL_OK, "OK", "sensor", [])
        app._refresh_ui()
        clock[0] += 11
        app._refresh_ui()
        await pilot.pause()
        assert len(notices) == 2
