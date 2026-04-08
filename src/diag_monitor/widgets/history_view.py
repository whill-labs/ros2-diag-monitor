from __future__ import annotations

from textual.widgets import Static

from diag_monitor.store import StatusChange, LEVEL_NAMES, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE

_LEVEL_STYLES = {LEVEL_OK: "green", LEVEL_WARN: "yellow", LEVEL_ERROR: "red", LEVEL_STALE: "dim"}


class HistoryView(Static):
    """Right-bottom pane: display status change history of the selected item."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def show_history(self, changes: list[StatusChange] | None) -> None:
        if not changes:
            self.update("[dim]No history[/]")
            return

        lines: list[str] = ["[bold]History:[/]"]
        for change in reversed(changes):
            time_str = change.timestamp.strftime("%H:%M:%S")
            new_style = _LEVEL_STYLES.get(change.new_level, "white")
            new_name = LEVEL_NAMES.get(change.new_level, "?")

            if change.prev_level is None:
                lines.append(f"  {time_str}  (first seen) [{new_style}]{new_name}[/]")
            else:
                prev_style = _LEVEL_STYLES.get(change.prev_level, "white")
                prev_name = LEVEL_NAMES.get(change.prev_level, "?")
                lines.append(
                    f"  {time_str}  [{prev_style}]{prev_name}[/] -> [{new_style}]{new_name}[/]"
                    f"  {change.message}"
                )

        self.update("\n".join(lines))
