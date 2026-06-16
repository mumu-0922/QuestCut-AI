"""
History Manager
===============
Small, UI-agnostic undo/redo stack used by the editor window.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import numpy as np
from PIL import Image


@dataclass
class HistoryState:
    """Serializable snapshot of a user-visible edit state."""
    mask: Any = None
    processed_image: Any = None
    control_settings: Dict[str, Any] = field(default_factory=dict)


class HistoryManager:
    """Owns undo/redo stack mechanics while callers own capture/restore details."""

    def __init__(
        self,
        *,
        capture_state: Callable[[], HistoryState],
        restore_state: Callable[[Optional[HistoryState]], None],
        has_state: Callable[[], bool],
        sync_after_mutation: Callable[[], None] | None = None,
        clear_aux_history: Callable[[], None] | None = None,
        changed_callback: Callable[[], None] | None = None,
        max_history: int = 30,
    ):
        self._capture_state = capture_state
        self._restore_state = restore_state
        self._has_state = has_state
        self._sync_after_mutation = sync_after_mutation or (lambda: None)
        self._clear_aux_history = clear_aux_history or (lambda: None)
        self._changed_callback = changed_callback or (lambda: None)
        self._max_history = max_history
        self._history_stack: list[HistoryState] = []
        self._redo_stack: list[HistoryState] = []
        self._baseline: HistoryState | None = None
        self.mutation_pending = False
        self.restoring = False

    @staticmethod
    def clone_mask(mask=None):
        if mask is None:
            return None
        if isinstance(mask, np.ndarray):
            return mask.copy()
        if isinstance(mask, Image.Image):
            return np.array(mask.convert('L'))
        return np.array(mask).copy()

    @staticmethod
    def clone_image(image=None):
        return image.copy() if image is not None else None

    @classmethod
    def clone_state(cls, state=None):
        if state is None:
            return None
        return HistoryState(
            mask=cls.clone_mask(state.mask),
            processed_image=cls.clone_image(state.processed_image),
            control_settings=dict(state.control_settings or {}),
        )

    @property
    def can_undo(self):
        return bool(self._history_stack)

    @property
    def can_redo(self):
        return bool(self._redo_stack)

    def _capture_or_none(self):
        return self._capture_state() if self._has_state() else None

    def _notify_changed(self):
        self._changed_callback()

    def reset(self):
        self._history_stack.clear()
        self._redo_stack.clear()
        self._baseline = None
        self.mutation_pending = False
        self._clear_aux_history()
        self._notify_changed()

    def mark_baseline(self):
        self._baseline = self._capture_or_none()
        self._history_stack.clear()
        self._redo_stack.clear()
        self.mutation_pending = False
        self._clear_aux_history()
        self._notify_changed()

    def push(self):
        """Save current edit state before a user-visible mutation."""
        if self.restoring or self.mutation_pending or not self._has_state():
            return None
        state = self.clone_state(self._baseline) if self._baseline is not None else self._capture_state()
        self._history_stack.append(state)
        if len(self._history_stack) > self._max_history:
            self._history_stack.pop(0)
        self._redo_stack.clear()
        self.mutation_pending = True
        self._notify_changed()
        return None

    def finish_mutation(self):
        """Record the post-mutation baseline and refresh edit controls."""
        if self.restoring:
            return None
        self._baseline = self._capture_or_none()
        self.mutation_pending = False
        self._sync_after_mutation()
        self._notify_changed()
        return None

    def cancel_mutation(self):
        """Drop a pending history point when the attempted mutation failed."""
        if self.mutation_pending and self._history_stack:
            self._history_stack.pop()
        self.mutation_pending = False
        self._baseline = self._capture_or_none()
        self._notify_changed()
        return None

    def _restore(self, state=None):
        if state is None:
            return None
        self.restoring = True
        try:
            self._restore_state(self.clone_state(state))
            self._baseline = self._capture_or_none()
            self.mutation_pending = False
        finally:
            self.restoring = False
        return None

    def undo(self):
        if not self._history_stack:
            return None
        current = self._capture_state()
        previous = self._history_stack.pop()
        self._redo_stack.append(current)
        if len(self._redo_stack) > self._max_history:
            self._redo_stack.pop(0)
        self._restore(previous)
        self._notify_changed()
        return None

    def redo(self):
        if not self._redo_stack:
            return None
        current = self._capture_state()
        next_state = self._redo_stack.pop()
        self._history_stack.append(current)
        if len(self._history_stack) > self._max_history:
            self._history_stack.pop(0)
        self._restore(next_state)
        self._notify_changed()
        return None
