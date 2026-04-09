from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static

from diag_monitor import __version__
from diag_monitor.store import DiagStore, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE
from diag_monitor.widgets.item_list import ItemList
from diag_monitor.widgets.detail_view import DetailView
from diag_monitor.widgets.history_view import HistoryView

_NO_DATA_TIMEOUT = 10.0  # seconds
_HEADER_LEVEL_CLASSES = {LEVEL_OK: "level-ok", LEVEL_WARN: "level-warn", LEVEL_ERROR: "level-error"}
_ALL_HEADER_LEVEL_CLASSES = set(_HEADER_LEVEL_CLASSES.values())


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

    def on_mount(self) -> None:
        self.set_interval(1.0, self._refresh_ui)

    def _refresh_ui(self) -> None:
        items, history = self._store.snapshot()

        # Update header
        topic = self._ros_bridge.topic if self._ros_bridge else "/diagnostics"
        total = len(items)
        warn_count = sum(1 for i in items.values() if i.level == LEVEL_WARN)
        error_count = sum(1 for i in items.values() if i.level == LEVEL_ERROR)
        header_text = f" diag-monitor  {topic}  \u25cf {total} items"
        if warn_count:
            header_text += f"  \u26a0 {warn_count}"
        if error_count:
            header_text += f"  \u2717 {error_count}"
        header = self.query_one("#header", Static)
        header.update(header_text)

        # Update header color based on worst level (STALE excluded)
        levels = [i.level for i in items.values() if i.level != LEVEL_STALE]
        worst = max(levels) if levels else None
        header.remove_class(*_ALL_HEADER_LEVEL_CLASSES)
        if worst is not None and worst in _HEADER_LEVEL_CLASSES:
            header.add_class(_HEADER_LEVEL_CLASSES[worst])

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
