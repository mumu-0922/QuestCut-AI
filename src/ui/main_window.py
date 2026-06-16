"""
Legacy MainWindow compatibility wrapper.

The active application window is EliteMainWindow.  Older imports of
``src.ui.main_window.MainWindow`` are kept working by aliasing to the modern
implementation instead of loading the incomplete legacy UI recovered from bytecode.
"""

from .elite_main_window import EliteMainWindow


class MainWindow(EliteMainWindow):
    """Backward-compatible alias for the active editor window."""

    pass
