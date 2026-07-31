import pytest

from diag_monitor.app import DiagMonitorApp, HelpScreen
from diag_monitor.store import DiagStore, LEVEL_OK


def make_store() -> DiagStore:
    store = DiagStore()
    store.update("ekf: frequency", LEVEL_OK, "OK", "ekf_node", [])
    return store


async def test_question_mark_opens_the_help_modal():
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        assert len(app.screen_stack) == 1

        await pilot.press("?")
        await pilot.pause()

        assert isinstance(app.screen, HelpScreen)


@pytest.mark.parametrize("key", ["escape", "?"])
async def test_help_modal_closes(key: str):
    app = DiagMonitorApp(make_store())
    async with app.run_test() as pilot:
        await pilot.press("?")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)

        await pilot.press(key)
        await pilot.pause()

        assert len(app.screen_stack) == 1
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.parametrize("size", [(120, 40), (100, 30), (80, 24), (60, 24), (50, 20)])
async def test_help_dialog_is_not_squeezed_by_the_main_grid(size):
    """`HelpScreen` must not inherit the `Screen` grid from app.css.

    The grid would confine the dialog to one 1fr column of `1fr 2fr`, so it
    never reached its declared width and wrapped tall enough to overflow the
    bottom of the screen on narrower terminals.
    """
    app = DiagMonitorApp(make_store())
    async with app.run_test(size=size) as pilot:
        await pilot.press("?")
        await pilot.pause()

        region = app.screen.query_one("#help-dialog").region
        assert region.width == 45, f"expected the declared width, got {region.width}"
        assert region.x >= 0 and region.y >= 0
        assert region.right <= size[0]
        assert region.bottom <= size[1]


@pytest.mark.parametrize("size", [(40, 16), (30, 10), (24, 8)])
async def test_help_dialog_stays_inside_tiny_terminals(size):
    """Below the dialog's declared size, max-width/max-height clamp it."""
    app = DiagMonitorApp(make_store())
    async with app.run_test(size=size) as pilot:
        await pilot.press("?")
        await pilot.pause()

        region = app.screen.query_one("#help-dialog").region
        assert region.x >= 0 and region.y >= 0
        assert region.right <= size[0]
        assert region.bottom <= size[1]
