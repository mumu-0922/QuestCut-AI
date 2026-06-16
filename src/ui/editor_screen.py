"""
Editor Screen for QuestCut-AI
==========================
Main editor workspace with canvas, toolbar, and filmstrip.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon

from .batch_filmstrip import BatchFilmstrip
from .canvas_widget import CanvasWidget
from .control_panel import ControlPanel
from ..utils.i18n import tr


class EditorToolButton(QPushButton):
    """A styled toolbar button for the editor."""

    tool_changed = Signal(str, bool)

    def __init__(self, icon_name=None, fallback=None, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        if fallback:
            self.setText(fallback)
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #2a2a2f;
                border: 1px solid #3a3a40;
                border-radius: 8px;
                color: #a0a0a5;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a3a40;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #4F46E5;
                border-color: #4F46E5;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1f1f23;
                border-color: #24242a;
                color: #606065;
            }
            """
        )

    def _connect_signals(self):
        pass


class EditorToolbar(QWidget):
    """Top toolbar for the editor."""

    view_toggled = Signal(str)
    undo_clicked = Signal()
    redo_clicked = Signal()
    compare_toggled = Signal(bool)
    auto_enhance_clicked = Signal()
    back_clicked = Signal()
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    zoom_fit_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setFixedHeight(56)
        self.setStyleSheet(
            """
            EditorToolbar {
                background-color: #1a1a1d;
                border-bottom: 1px solid #2a2a2f;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.back_btn = QPushButton(tr('Back'))
        self.back_btn.setFixedHeight(36)
        self.back_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.back_btn)

        layout.addStretch()

        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(36, 36)
        self.zoom_out_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.zoom_out_btn)

        self.zoom_fit_btn = QPushButton(tr('Fit'))
        self.zoom_fit_btn.setFixedHeight(36)
        self.zoom_fit_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.zoom_fit_btn)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(36, 36)
        self.zoom_in_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.zoom_in_btn)

        self.undo_btn = QPushButton(tr('Undo'))
        self.undo_btn.setFixedHeight(36)
        self.undo_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton(tr('Redo'))
        self.redo_btn.setFixedHeight(36)
        self.redo_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.redo_btn)

        self.compare_btn = QPushButton(tr('Compare'))
        self.compare_btn.setCheckable(True)
        self.compare_btn.setFixedHeight(36)
        self.compare_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.compare_btn)

        self.auto_enhance_btn = QPushButton(tr('Enhance'))
        self.auto_enhance_btn.setFixedHeight(36)
        self.auto_enhance_btn.setStyleSheet(self._btn_style())
        layout.addWidget(self.auto_enhance_btn)
        self.set_undo_enabled(False)
        self.set_redo_enabled(False)

    def _btn_style(self):
        return (
            """
            QPushButton {
                background-color: #2a2a2f;
                border: 1px solid #3a3a40;
                border-radius: 6px;
                color: #a0a0a5;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #3a3a40;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #4F46E5;
                border-color: #4F46E5;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1f1f23;
                border-color: #24242a;
                color: #606065;
            }
            """
        )


    def retranslate_ui(self):
        self.back_btn.setText(tr('Back'))
        self.zoom_fit_btn.setText(tr('Fit'))
        self.undo_btn.setText(tr('Undo'))
        self.redo_btn.setText(tr('Redo'))
        self.compare_btn.setText(tr('Compare'))
        self.auto_enhance_btn.setText(tr('Enhance'))

    def set_undo_enabled(self, enabled=None):
        self.undo_btn.setEnabled(bool(enabled))

    def set_redo_enabled(self, enabled=None):
        self.redo_btn.setEnabled(bool(enabled))

    def _connect_signals(self):
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.redo_btn.clicked.connect(self.redo_clicked.emit)
        self.compare_btn.toggled.connect(self.compare_toggled.emit)
        self.auto_enhance_btn.clicked.connect(self.auto_enhance_clicked.emit)
        self.zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        self.zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        self.zoom_fit_btn.clicked.connect(self.zoom_fit_clicked.emit)


class EditorScreen(QWidget):
    """Main editor workspace with canvas, toolbar, filmstrip, and control panel."""

    back_requested = Signal()
    tool_changed = Signal(str, bool)
    brush_size_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = EditorToolbar()
        layout.addWidget(self.toolbar)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.canvas = CanvasWidget()
        content_layout.addWidget(self.canvas, 1)

        self.control_panel = ControlPanel()
        content_layout.addWidget(self.control_panel)

        layout.addWidget(content, 1)

        self.filmstrip = BatchFilmstrip()
        self.filmstrip.hide()
        layout.addWidget(self.filmstrip)

    def _connect_signals(self):
        self.toolbar.back_clicked.connect(self.back_requested.emit)
        self.toolbar.view_toggled.connect(lambda v: self.tool_changed.emit('view', bool(v)))
        self.toolbar.zoom_in_clicked.connect(self.canvas.zoom_in)
        self.toolbar.zoom_out_clicked.connect(self.canvas.zoom_out)
        self.toolbar.zoom_fit_clicked.connect(self.canvas.zoom_fit)
        self.canvas.brush_stroke.connect(lambda pts, r, add: self.tool_changed.emit('brush', add))


    def retranslate_ui(self):
        self.toolbar.retranslate_ui()
        self.control_panel.retranslate_ui()
        self.filmstrip.retranslate_ui()

    def set_status(self, message):
        """Set status message."""
        if hasattr(self.control_panel, 'set_status'):
            self.control_panel.set_status(message)
