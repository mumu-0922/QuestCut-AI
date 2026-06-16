'''
Loading Overlay for QuestCut-AI
===========================
Loading states, progress indicators, and UI blocking.
'''
import logging
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFrame
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from ..utils.i18n import tr
logger = logging.getLogger(__name__)
class _SpinnerWidget(QWidget):
    '''Widget that paints a spinning arc inside its own paintEvent.'''
    def paintEvent(self, event):
        overlay = self.parent()
        if not isinstance(overlay, LoadingOverlay):
            return None
        if not overlay._spinner_timer.isActive():
            return None
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        radius = 20
        pen = QPen(QColor('#4F46E5'), 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.drawArc(rect, overlay._spinner_angle * 16, 4320)
        painter.end()
class LoadingOverlay(QWidget):
    '''
    Overlay widget that covers parent during loading operations.
    Features:
    - Semi-transparent background
    - Spinner or progress bar
    - Status message
    - Cancel button (optional)
    '''
    cancel_clicked = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._setup_ui()
        self._spinner_angle = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._update_spinner)
        self.hide()
    def _setup_ui(self):
        '''Setup the overlay UI.'''
        self.setStyleSheet('\n            LoadingOverlay {\n                background-color: rgba(15, 15, 16, 0.85);\n            }\n        ')
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        content = QFrame()
        content.setStyleSheet('\n            QFrame {\n                background-color: #1a1a1d;\n                border: 1px solid #2a2a2f;\n                border-radius: 12px;\n                padding: 24px;\n            }\n        ')
        content.setFixedWidth(320)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        self._spinner_widget = _SpinnerWidget(self)
        self._spinner_widget.setFixedSize(48, 48)
        content_layout.addWidget(self._spinner_widget, Qt.AlignCenter)
        self._status_label = QLabel(tr('Processing...'))
        self._status_label.setStyleSheet('\n            QLabel {\n                color: #ffffff;\n                font-size: 14px;\n                font-weight: 600;\n            }\n        ')
        self._status_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self._status_label)
        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet('\n            QProgressBar {\n                background-color: #2a2a2f;\n                border: none;\n                border-radius: 4px;\n                height: 8px;\n                text-align: center;\n            }\n            QProgressBar::chunk {\n                background-color: #4F46E5;\n                border-radius: 4px;\n            }\n        ')
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        content_layout.addWidget(self._progress_bar)
        self._details_label = QLabel('')
        self._details_label.setStyleSheet('\n            QLabel {\n                color: #a0a0a5;\n                font-size: 12px;\n            }\n        ')
        self._details_label.setAlignment(Qt.AlignCenter)
        self._details_label.setWordWrap(True)
        content_layout.addWidget(self._details_label)
        self._cancel_btn = QPushButton(tr('Cancel'))
        self._cancel_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 6px;\n                padding: 8px 24px;\n                color: #ffffff;\n                font-weight: 500;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n            }\n        ')
        self._cancel_btn.clicked.connect(self.cancel_clicked.emit)
        self._cancel_btn.hide()
        content_layout.addWidget(self._cancel_btn, Qt.AlignCenter)
        layout.addWidget(content)
    def show_loading(self, message=None, details='', show_progress=True, show_cancel=False, indeterminate=False):
        '''
        Show the loading overlay.
        Args:
            message: Main status message
            details: Additional details
            show_progress: Show progress bar
            show_cancel: Show cancel button
            indeterminate: Use indeterminate progress
        '''
        self._status_label.setText(message or tr('Processing...'))
        self._details_label.setText(details)
        self._details_label.setVisible(bool(details))
        self._progress_bar.setVisible(show_progress)
        if indeterminate:
            self._progress_bar.setRange(0, 0)
        else:
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
        self._cancel_btn.setVisible(show_cancel)
        self._spinner_timer.start(50)
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
    def update_progress(self, value=None, message=None, details=None):
        '''
        Update progress.
        Args:
            value: Progress value (0.0 to 1.0)
            message: Optional new message
            details: Optional new details
        '''
        self._progress_bar.setValue(int(value * 100))
        if message is not None:
            self._status_label.setText(message)
        if details is not None:
            self._details_label.setText(details)
            self._details_label.setVisible(bool(details))
            return None
    def hide_loading(self):
        '''Hide the loading overlay.'''
        self._spinner_timer.stop()
        self.hide()
    def _update_spinner(self):
        '''Update spinner animation.'''
        self._spinner_angle = (self._spinner_angle + 10) % 360
        self._spinner_widget.update()
    def paintEvent(self, event = None):
        '''Paint the overlay background.'''
        super().paintEvent(event)
    def resizeEvent(self, event = None):
        '''Handle resize to match parent.'''
        super().resizeEvent(event)
        if self.parent() and self.isVisible():
            parent_rect = self.parent().rect()
            if self.geometry() != parent_rect:
                self.setGeometry(parent_rect)
                return None
    def retranslate_ui(self):
        '''Refresh language-dependent labels.'''
        self._cancel_btn.setText(tr('Cancel'))
        if self._status_label.text() in ('Processing...', '处理中...'):
            self._status_label.setText(tr('Processing...'))
class LoadingStateManager:
    '''
    Manages loading states for multiple widgets.
    Tracks which operations are in progress and manages
    widget enabled states accordingly.
    '''
    def __init__(self):
        self._loading_operations = set()
        self._disabled_widgets = []
        self._overlay = None
    def set_overlay(self, overlay = None):
        '''Set the loading overlay widget.'''
        self._overlay = overlay
    def start_operation(self, operation_id=None, widgets_to_disable=None, message=None, show_progress=True, show_cancel=False):
        '''
        Start a loading operation.
        Args:
            operation_id: Unique identifier for the operation
            widgets_to_disable: List of widgets to disable
            message: Loading message
            show_progress: Show progress bar
            show_cancel: Show cancel button
        '''
        self._loading_operations.add(operation_id)
        if widgets_to_disable:
            for widget in widgets_to_disable:
                if widget.isEnabled():
                    self._disabled_widgets.append(widget)
                    widget.setEnabled(False)
        if self._overlay:
            self._overlay.show_loading(message=message or tr('Processing...'), show_progress=show_progress, show_cancel=show_cancel)
            return None
    def update_operation(self, operation_id=None, progress=None, message=None, details=None):
        """Update an operation's progress."""
        if operation_id in self._loading_operations or self._overlay:
            self._overlay.update_progress(progress, message, details)
            return None
    def end_operation(self, operation_id = None):
        '''
        End a loading operation.
        Args:
            operation_id: The operation to end
        '''
        self._loading_operations.discard(operation_id)
        if not self._loading_operations:
            for widget in self._disabled_widgets:
                widget.setEnabled(True)
            self._disabled_widgets.clear()
            if self._overlay:
                self._overlay.hide_loading()
                return None
    def is_loading(self, operation_id = None):
        '''
        Check if loading.
        Args:
            operation_id: Specific operation, or None for any
        Returns:
            True if loading
        '''
        if operation_id:
            return operation_id in self._loading_operations
        return len(self._loading_operations) > 0
    def cancel_all(self):
        '''Cancel all operations.'''
        self._loading_operations.clear()
        for widget in self._disabled_widgets:
            widget.setEnabled(True)
        self._disabled_widgets.clear()
        if self._overlay:
            self._overlay.hide_loading()
            return None
_loading_manager: Optional[LoadingStateManager] = None
def get_loading_manager():
    '''Get the global loading state manager.'''
    global _loading_manager
    if _loading_manager is None:
        _loading_manager = LoadingStateManager()
    return _loading_manager
