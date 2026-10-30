from __future__ import annotations

from rich.markup import escape
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from diag_monitor.store import DiagItem, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE, LEVEL_NAMES, DiagnosticKey

_LEVEL_ORDER = [LEVEL_ERROR, LEVEL_WARN, LEVEL_STALE, LEVEL_OK]
_LEVEL_ICONS = {LEVEL_OK: "[green]\u25cf[/]", LEVEL_WARN: "[yellow]\u25cf[/]", LEVEL_ERROR: "[red]\u25cf[/]", LEVEL_STALE: "[dim]\u25cf[/]"}


class ItemList(Tree[DiagnosticKey]):
    """Left pane: display diagnostic items grouped by level."""

    def __init__(self, **kwargs) -> None:
        super().__init__("Diagnostics", **kwargs)
        self.show_root = False
        self.root.expand()
        self._selected_key: DiagnosticKey | None = None
        # Pre-create branches in _LEVEL_ORDER so ordering is always correct
        self._branches: dict[int, TreeNode] = {}
        for level in _LEVEL_ORDER:
            icon = _LEVEL_ICONS[level]
            branch = self.root.add(f"{icon} {LEVEL_NAMES[level]} (0)", expand=True)
            self._branches[level] = branch
        self._leaves: dict[DiagnosticKey, TreeNode] = {}
        self._leaf_levels: dict[DiagnosticKey, int] = {}

    @property
    def selected_key(self) -> DiagnosticKey | None:
        return self._selected_key

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data is not None:
            self._selected_key = event.node.data

    def _ensure_branch(self, level: int) -> TreeNode:
        return self._branches[level]

    def _update_branch_label(self, level: int) -> None:
        branch = self._branches[level]
        count = len(branch.children)
        icon = _LEVEL_ICONS[level]
        branch.set_label(f"{icon} {LEVEL_NAMES[level]} ({count})")

    def refresh_items(self, items: dict[DiagnosticKey, DiagItem]) -> None:
        selected = self._selected_key
        selected_moved = False
        current_names = set(items.keys())
        known_names = set(self._leaves.keys())

        # Remove disappeared items
        for name in known_names - current_names:
            old_level = self._leaf_levels.pop(name)
            self._leaves.pop(name).remove()
            self._update_branch_label(old_level)

        # Add new items and move items that changed level
        levels_to_update: set[int] = set()
        for name, item in items.items():
            level = item.level if item.level in _LEVEL_ICONS else LEVEL_STALE
            icon = _LEVEL_ICONS[level]
            label = f"{icon} {escape(item.name)} ({escape(item.hardware_id or 'no hardware ID')})"

            if name not in self._leaves:
                # New item
                branch = self._ensure_branch(level)
                node = branch.add_leaf(label, data=name)
                self._leaves[name] = node
                self._leaf_levels[name] = level
                levels_to_update.add(level)
            elif self._leaf_levels[name] != level:
                selected_moved |= name == selected
                # Level changed: remove from old branch, add to new
                old_level = self._leaf_levels[name]
                self._leaves[name].remove()
                branch = self._ensure_branch(level)
                node = branch.add_leaf(label, data=name)
                self._leaves[name] = node
                self._leaf_levels[name] = level
                levels_to_update.add(old_level)
                levels_to_update.add(level)

        for level in levels_to_update:
            self._update_branch_label(level)

        if selected_moved and selected in self._leaves:
            self._leaves[selected].parent.expand()
            self.call_after_refresh(self.select_node, self._leaves[selected])
