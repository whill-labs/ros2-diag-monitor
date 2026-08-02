from textual.widgets import Input, Static

from diag_monitor.app import DiagMonitorApp
from diag_monitor.store import DiagStore, LEVEL_OK, LEVEL_WARN


def make_store() -> DiagStore:
    store = DiagStore()
    store.update("ekf: frequency", LEVEL_OK, "OK", "ekf_node", [])
    store.update("imu: temperature", LEVEL_WARN, "Too hot", "imu_node", [])
    store.update("motor/left: current", LEVEL_OK, "OK", "motor_node", [])
    return store


def leaf_names(app: DiagMonitorApp) -> set[str]:
    """Item names currently shown as leaves in the left pane."""
    item_list = app.query_one("#item-list")
    return {node.data for branch in item_list.root.children for node in branch.children}


def header_text(app: DiagMonitorApp) -> str:
    """Plain text (markup resolved) of the header."""
    return str(app.query_one("#header", Static).visual)


async def apply_filter(app, pilot, text: str) -> None:
    """Press `/`, type the filter text, and let the periodic refresh run."""
    await pilot.press("/")
    await pilot.press(*text)
    app._refresh_ui()
    await pilot.pause()


async def test_filter_input_is_hidden_until_slash():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        assert app.query_one("#filter-input").display is False
        assert app.focused.id == "item-list"

        await pilot.press("/")
        await pilot.pause()

        assert app.query_one("#filter-input").display is True
        assert app.focused.id == "filter-input"


async def test_filter_narrows_item_list():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()
        assert len(leaf_names(app)) == 3

        await apply_filter(app, pilot, "motor")

        assert leaf_names(app) == {"motor/left: current"}


async def test_filter_matches_substring_case_insensitively():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "IMU")

        assert leaf_names(app) == {"imu: temperature"}


async def test_filter_with_no_match_empties_item_list():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "nonexistent")

        assert leaf_names(app) == set()


async def test_header_counts_ignore_the_filter():
    """Counts and the filter indicator both come from the unfiltered snapshot."""
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "ekf")

        text = header_text(app)
        assert "3 items" in text  # not 1
        assert "⚠ 1" in text  # WARN item is filtered out of the list but still counted
        assert "Filter: ekf" in text


async def test_header_has_no_filter_indicator_when_filter_is_empty():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        app._refresh_ui()
        await pilot.pause()

        assert "Filter:" not in header_text(app)


async def test_filter_text_is_escaped_in_header():
    """Square brackets must reach the header literally, not as Rich markup."""
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "[b]imu")

        assert "Filter: [b]imu" in header_text(app)


async def test_escape_clears_the_filter_and_hides_the_input():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "motor")
        assert leaf_names(app) == {"motor/left: current"}

        await pilot.press("escape")
        app._refresh_ui()
        await pilot.pause()

        filter_input = app.query_one("#filter-input", Input)
        assert filter_input.value == ""
        assert filter_input.display is False
        assert app.focused.id == "item-list"
        assert len(leaf_names(app)) == 3
        assert "Filter:" not in header_text(app)


async def test_enter_returns_focus_to_item_list_and_keeps_the_filter():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "motor")

        await pilot.press("enter")
        app._refresh_ui()
        await pilot.pause()

        assert app.focused.id == "item-list"
        assert app.query_one("#filter-input", Input).value == "motor"
        assert leaf_names(app) == {"motor/left: current"}


async def test_slash_and_question_mark_are_typed_into_the_filter():
    """While the filter has focus, its own keybindings must not swallow input."""
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await apply_filter(app, pilot, "motor/?")

        assert app.query_one("#filter-input", Input).value == "motor/?"
        assert len(app.screen_stack) == 1  # help modal was not pushed
