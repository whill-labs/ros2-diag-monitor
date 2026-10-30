import pytest

from diag_monitor.app import DiagMonitorApp
from diag_monitor.store import DiagStore, LEVEL_OK, LEVEL_ERROR


def test_same_name_keeps_independent_device_statuses_and_histories():
    store = DiagStore()
    store.update("lidar: connection", LEVEL_ERROR, "Lost", "front", [("port", "1")])
    store.update("lidar: connection", LEVEL_OK, "Connected", "rear", [("port", "2")])
    store.update("lidar: connection", LEVEL_OK, "Connected", "rear", [])
    items, history = store.snapshot()
    assert len(items) == 2
    assert items[("lidar: connection", "front")].level == LEVEL_ERROR
    assert items[("lidar: connection", "rear")].level == LEVEL_OK
    assert len(history[("lidar: connection", "front")]) == 1
    assert len(history[("lidar: connection", "rear")]) == 1


def test_tuple_identity_has_no_separator_collisions_and_allows_empty_hardware():
    store = DiagStore()
    for name, hardware in (("a:b", "c"), ("a", "b:c"), ("a", "")):
        store.update(name, LEVEL_OK, "OK", hardware, [])
    assert len(store.snapshot()[0]) == 3


@pytest.mark.parametrize("hardware", ["front", "rear"])
async def test_select_each_device_and_keep_selection_when_level_changes(hardware):
    store = DiagStore()
    name = "lidar: connection"
    store.update(name, LEVEL_ERROR, "Front lost", "front", [("port", "front_port")])
    store.update(name, LEVEL_OK, "Rear ready", "rear", [("port", "rear_port")])
    app = DiagMonitorApp(store)
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()
        tree = app.query_one("#item-list")
        assert len(tree._leaves) == 2
        for key, leaf in tree._leaves.items():
            assert key[1] in leaf.label.plain
        key = (name, hardware)
        tree.move_cursor(tree._leaves[key])
        await pilot.pause()
        app._refresh_ui()
        assert f"{hardware}_port" in str(app.query_one("#detail-view").visual)
        assert tree.selected_key == key
        destination = LEVEL_OK if hardware == "front" else LEVEL_ERROR
        tree._branches[destination].collapse()
        store.update(name, LEVEL_OK if hardware == "front" else LEVEL_ERROR,
                     "Changed", hardware, [("port", f"{hardware}_port")])
        app._refresh_ui()
        await pilot.pause()
        app._refresh_ui()
        assert tree.selected_key == key
        assert tree.cursor_node.data == key
        assert f"{hardware}_port" in str(app.query_one("#detail-view").visual)
        await pilot.press("/")
        await pilot.press(*"lidar")
        app._refresh_ui()
        await pilot.pause()
        assert len(tree._leaves) == 2
        assert "2 items" in str(app.query_one("#header").visual)
