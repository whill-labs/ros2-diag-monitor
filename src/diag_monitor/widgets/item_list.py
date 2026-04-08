from __future__ import annotations

from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from diag_monitor.store import DiagItem, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_STALE, LEVEL_NAMES

_LEVEL_ORDER = [LEVEL_ERROR, LEVEL_WARN, LEVEL_STALE, LEVEL_OK]
_LEVEL_ICONS = {LEVEL_OK: "[green]\u25cf[/]", LEVEL_WARN: "[yellow]\u25cf[/]", LEVEL_ERROR: "[red]\u25cf[/]", LEVEL_STALE: "[dim]\u25cf[/]"}


class ItemList(Tree[str]):
    """Left pane: display diagnostic items grouped by level."""

    def __init__(self, **kwargs) -> None:
        super().__init__("Diagnostics", **kwargs)
        self.show_root = False
        self.root.expand()
        self._selected_name: str | None = None
        # Track nodes for diff updates
        self._branches: dict[int, TreeNode] = {}
        self._leaves: dict[str, TreeNode] = {}
        self._leaf_levels: dict[str, int] = {}

    @property
    def selected_name(self) -> str | None:
        return self._selected_name

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data is not None:
            self._selected_name = event.node.data

    def _ensure_branch(self, level: int) -> TreeNode:
        if level not in self._branches:
            icon = _LEVEL_ICONS[level]
            branch = self.root.add(f"{icon} {LEVEL_NAMES[level]} (0)", expand=True)
            self._branches[level] = branch
        return self._branches[level]

    def _update_branch_label(self, level: int) -> None:
        if level not in self._branches:
            return
        branch = self._branches[level]
        count = len(branch.children)
        if count == 0:
            branch.remove()
            del self._branches[level]
        else:
            icon = _LEVEL_ICONS[level]
            branch.set_label(f"{icon} {LEVEL_NAMES[level]} ({count})")

    def refresh_items(self, items: dict[str, DiagItem]) -> None:
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

            if name not in self._leaves:
                # New item
                branch = self._ensure_branch(level)
                node = branch.add_leaf(f"{icon} {item.name}", data=name)
                self._leaves[name] = node
                self._leaf_levels[name] = level
                levels_to_update.add(level)
            elif self._leaf_levels[name] != level:
                # Level changed: remove from old branch, add to new
                old_level = self._leaf_levels[name]
                self._leaves[name].remove()
                branch = self._ensure_branch(level)
                node = branch.add_leaf(f"{icon} {item.name}", data=name)
                self._leaves[name] = node
                self._leaf_levels[name] = level
                levels_to_update.add(old_level)
                levels_to_update.add(level)

        for level in levels_to_update:
            self._update_branch_label(level)
