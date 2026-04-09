#!/usr/bin/env python3
"""Minimal test: does Textual inline style color change work in this terminal?"""

from textual.app import App, ComposeResult
from textual.widgets import Static


class ColorTestApp(App):
    CSS = """
    #header { column-span: 2; height: 1; text-align: center; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Starting...", id="header")

    def on_mount(self) -> None:
        h = self.query_one("#header", Static)
        h.styles.background = "#444444"
        h.styles.color = "white"
        self._index = 0
        self.set_interval(3.0, self._cycle)

    def _cycle(self) -> None:
        colors = [
            ("#2e7d32", "white", "GREEN (OK)"),
            ("#f9a825", "black", "YELLOW (WARN)"),
            ("#c62828", "white", "RED (ERROR)"),
        ]
        bg, fg, label = colors[self._index % 3]
        h = self.query_one("#header", Static)
        h.styles.background = bg
        h.styles.color = fg
        h.update(f" {label}  bg={bg}")
        self._index += 1


if __name__ == "__main__":
    ColorTestApp().run()
