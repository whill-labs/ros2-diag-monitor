from __future__ import annotations

from rich.markup import escape
from rich.text import Text
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

        lines: list[str] = ["[bold]History (state / cause changes):[/]"]
        for change in reversed(changes):
            time_str = change.timestamp.strftime("%H:%M:%S")
            new_style = _LEVEL_STYLES.get(change.new_level, "white")
            new_name = LEVEL_NAMES.get(change.new_level, "?")

            if change.prev_level is None:
                lines.append(f"  {time_str}  (first seen) [{new_style}]{new_name}[/]")
            elif change.prev_level == change.new_level:
                lines.append(f"  {time_str}  [{new_style}]{new_name}[/] (details changed)")
            else:
                prev_style = _LEVEL_STYLES.get(change.prev_level, "white")
                prev_name = LEVEL_NAMES.get(change.prev_level, "?")
                lines.append(
                    f"  {time_str}  [{prev_style}]{prev_name}[/] -> [{new_style}]{new_name}[/]"
                )
            lines.append(f"    {escape(change.message)}")
            if change.hardware_id:
                lines.append(f"    HW ID: {escape(change.hardware_id)}")
            for key, value in change.values:
                lines.append(f"    {escape(key)}: {escape(value)}")

        self.update(Text.from_markup("\n".join(lines)))
