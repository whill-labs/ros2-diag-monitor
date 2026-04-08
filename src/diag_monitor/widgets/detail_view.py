from __future__ import annotations

from textual.widgets import Static

from diag_monitor.store import DiagItem, LEVEL_NAMES, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE

_LEVEL_STYLES = {LEVEL_OK: "green", LEVEL_WARN: "yellow", LEVEL_ERROR: "red", LEVEL_STALE: "dim"}


class DetailView(Static):
    """Right-top pane: display details of the selected item."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def show_item(self, item: DiagItem | None) -> None:
        if item is None:
            self.update("Select an item to view details")
            return

        level_name = LEVEL_NAMES.get(item.level, "UNKNOWN")
        style = _LEVEL_STYLES.get(item.level, "white")

        lines: list[str] = [
            f"[bold]Name:[/] {item.name}",
            f"[bold]Level:[/] [{style}]{level_name}[/]",
            f"[bold]Message:[/] {item.message}",
            f"[bold]HW ID:[/] {item.hardware_id}",
            f"[bold]Updated:[/] {item.last_updated.strftime('%H:%M:%S')}",
        ]

        if item.values:
            lines.append("")
            lines.append("[bold]Key-Values:[/]")
            for key, value in item.values:
                lines.append(f"  {key}: {value}")

        self.update("\n".join(lines))
