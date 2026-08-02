from datetime import datetime

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from diag_monitor import __version__
from diag_monitor.store import DiagStore, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE
from diag_monitor.widgets.detail_view import DetailView
from diag_monitor.widgets.history_view import HistoryView
from diag_monitor.widgets.item_list import ItemList

_NO_DATA_TIMEOUT = 10.0  # seconds
_HEADER_LEVEL_CLASSES = {LEVEL_OK: "level-ok", LEVEL_WARN: "level-warn", LEVEL_ERROR: "level-error"}
_ALL_HEADER_LEVEL_CLASSES = set(_HEADER_LEVEL_CLASSES.values())


class _FilterInput(Input):
    """Filter input that dismisses on Escape."""

    def key_escape(self) -> None:
        self.value = ""
        self.display = False
        self.screen.query_one("#item-list").focus()


class HelpScreen(ModalScreen):
    """Modal help screen."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                "[b]Keybindings[/b]\n"
                "\n"
                "  [b]/[/b]         Filter items by name\n"
                "  [b]?[/b]         Show this help\n"
                "  [b]t[/b]         Switch topic\n"
                "  [b]R[/b]         Reload subscription\n"
                "  [b]Tab[/b]       Switch pane\n"
                "  [b]\u2191[/b] [b]\u2193[/b]       Navigate\n"
                "  [b]q[/b]         Quit\n"
                "\n"
                "Press [b]Esc[/b] or [b]?[/b] to close"
            ),
            id="help-dialog",
        )


class DiagMonitorApp(App):
    CSS_PATH = "app.css"
    TITLE = "diag-monitor"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("slash", "filter", "Filter"),
        ("question_mark", "help", "Help"),
        ("t", "switch_topic", "Switch Topic"),
        ("R", "reload", "Reload"),
    ]

    def __init__(self, store: DiagStore, ros_bridge=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._ros_bridge = ros_bridge
        self._no_data_notified: bool = False
        self._monitor_start: datetime = datetime.now()
        self._filter_text: str = ""

    def compose(self) -> ComposeResult:
        topic = self._ros_bridge.topic if self._ros_bridge else "/diagnostics"
        yield Static(f" diag-monitor  {topic}  Loading...", id="header")
        yield ItemList(id="item-list")
        yield Container(
            DetailView(id="detail-view"),
            HistoryView(id="history-view"),
            id="right-pane",
        )
        yield Static(
            f" q:Quit  /:Filter  Tab:Pane  t:Topic  R:Reload  ?:Help"
            f"  │  v{__version__}  [@click=app.open_repo]github.com/whill-labs/ros2-diag-monitor[/]",
            id="footer",
        )
        yield _FilterInput(placeholder="Filter by name...", id="filter-input")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._refresh_ui)

    def _refresh_ui(self) -> None:
        items, history = self._store.snapshot()

        # Update header (always from unfiltered items)
        topic = self._ros_bridge.topic if self._ros_bridge else "/diagnostics"
        total = len(items)
        warn_count = sum(1 for i in items.values() if i.level == LEVEL_WARN)
        error_count = sum(1 for i in items.values() if i.level == LEVEL_ERROR)
        header_text = f" diag-monitor  {topic}  \u25cf {total} items"
        if warn_count:
            header_text += f"  \u26a0 {warn_count}"
        if error_count:
            header_text += f"  \u2717 {error_count}"
        if self._filter_text:
            header_text += f"  \u2502  Filter: {escape(self._filter_text)}"
        header = self.query_one("#header", Static)
        header.update(header_text)

        # Update header color based on worst level (STALE excluded)
        levels = [i.level for i in items.values() if i.level != LEVEL_STALE]
        worst = max(levels) if levels else None
        header.remove_class(*_ALL_HEADER_LEVEL_CLASSES)
        if worst is not None and worst in _HEADER_LEVEL_CLASSES:
            header.add_class(_HEADER_LEVEL_CLASSES[worst])

        # Apply filter for item list display
        if self._filter_text:
            filter_lower = self._filter_text.lower()
            items = {k: v for k, v in items.items() if filter_lower in v.name.lower()}

        # Update left pane
        item_list = self.query_one("#item-list", ItemList)
        item_list.refresh_items(items)

        # Update right pane
        selected = item_list.selected_name
        detail = self.query_one("#detail-view", DetailView)
        history_view = self.query_one("#history-view", HistoryView)

        if selected and selected in items:
            detail.show_item(items[selected])
            history_view.show_history(history.get(selected))
        else:
            detail.show_item(None)
            history_view.show_history(None)

        # No-data timeout: suggest switching to /diagnostics
        if not self._no_data_notified and self._ros_bridge is not None:
            last = self._store.last_msg_time
            ref = last if last is not None else self._monitor_start
            elapsed = (datetime.now() - ref).total_seconds()
            if elapsed >= _NO_DATA_TIMEOUT:
                self._no_data_notified = True
                topic = self._ros_bridge.topic
                alt = "/diagnostics" if topic == "/diagnostics_agg" else "/diagnostics_agg"
                self.notify(
                    f"No data on {topic} for {int(elapsed)}s. Press [b]t[/b] to switch to {alt}",
                    severity="warning",
                    timeout=10,
                )

    def action_reload(self) -> None:
        if self._ros_bridge is None:
            return
        self._ros_bridge.reload()
        self._no_data_notified = False
        self._monitor_start = datetime.now()
        self.notify("Reloaded")

    def action_open_repo(self) -> None:
        url = "https://github.com/whill-labs/ros2-diag-monitor"
        self.copy_to_clipboard(url)
        self.notify(f"Copied: {url}")

    def action_switch_topic(self) -> None:
        if self._ros_bridge is None:
            return
        current = self._ros_bridge.topic
        new_topic = "/diagnostics_agg" if current == "/diagnostics" else "/diagnostics"
        self._ros_bridge.switch_topic(new_topic)
        self._no_data_notified = False
        self._monitor_start = datetime.now()

    def action_filter(self) -> None:
        filter_input = self.query_one("#filter-input", _FilterInput)
        filter_input.display = True
        filter_input.focus()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._filter_text = event.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            self.query_one("#item-list", ItemList).focus()
