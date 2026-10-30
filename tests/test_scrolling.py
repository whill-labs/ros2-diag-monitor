import pytest

from diag_monitor.app import DiagMonitorApp
from diag_monitor.store import DiagStore


def make_store():
    store = DiagStore()
    store.update("sensor", 2, "Error", "device",
                 [(f"field_{i:02d}", f"value_{i:02d} [Hz]") for i in range(40)])
    for i in range(30):
        store.update("sensor", i % 2, f"Event {i}", "device", [])
    store.update("sensor", 2, "Error", "device",
                 [(f"field_{i:02d}", f"value_{i:02d} [Hz]") for i in range(40)])
    store.update("other", 0, "OK", "other_device", [])
    return store


async def select_sensor(app, pilot):
    app._refresh_ui()
    await pilot.pause()
    tree = app.query_one("#item-list")
    tree.move_cursor(tree._leaves["sensor"])
    await pilot.pause()
    app._refresh_ui()
    await pilot.pause()


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
async def test_details_and_history_are_keyboard_scrollable(size, monkeypatch):
    app = DiagMonitorApp(make_store())
    copied = []
    monkeypatch.setattr(app, "copy_to_clipboard", copied.append)
    async with app.run_test(size=size) as pilot:
        await select_sensor(app, pilot)
        assert "field_39" not in app.export_screenshot()
        await pilot.press("c")
        assert "field_39: value_39 [Hz]" in copied[0]
        await pilot.press("tab")
        assert app.focused.id == "detail-pane"
        await pilot.press("pagedown")
        await pilot.pause()
        assert app.query_one("#detail-pane").scroll_y > 0
        await pilot.press("end")
        await pilot.pause()
        details = app.query_one("#detail-pane")
        assert details.scroll_y > 0
        assert "field_39" in app.export_screenshot()
        position = details.scroll_y
        app._refresh_ui()
        await pilot.pause()
        assert details.scroll_y == position
        await pilot.press("tab")
        assert app.focused.id == "history-pane"
        await pilot.press("pagedown")
        await pilot.pause()
        assert app.query_one("#history-pane").scroll_y > 0
        await pilot.press("end")
        await pilot.pause()
        assert app.query_one("#history-pane").scroll_y > 0
        assert "first" in app.export_screenshot()
        await pilot.press("tab")
        assert app.focused.id == "item-list"
        tree = app.query_one("#item-list")
        tree.move_cursor(tree._leaves["other"])
        await pilot.pause()
        app._refresh_ui()
        await pilot.pause()
        assert details.scroll_y == 0
        assert app.query_one("#history-pane").scroll_y == 0


async def test_copy_contains_all_literal_fields_and_duplicate_keys(monkeypatch):
    store = DiagStore()
    store.update("sensor", 2, "Value [/ ]", "device",
                 [("rate", "20 [Hz]"), ("rate", "5 [Hz]"), ("note", "sensor [/]")])
    app = DiagMonitorApp(store)
    copied = []
    monkeypatch.setattr(app, "copy_to_clipboard", copied.append)
    async with app.run_test(size=(80, 24)) as pilot:
        await select_sensor(app, pilot)
        await pilot.press("c")
        assert "rate: 20 [Hz]" in copied[0]
        assert "rate: 5 [Hz]" in copied[0]
        assert "note: sensor [/]" in copied[0]
        assert "HW ID: device" in copied[0]
        await pilot.press("/")
        await pilot.press("c")
        assert app.query_one("#filter-input").value == "c"
        assert len(copied) == 1
