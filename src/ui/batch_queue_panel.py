"""
Batch Queue Panel for QuestCut-AI
=============================
Visual batch processing UI with progress, controls, and thumbnails.
"""
import logging
import time
from pathlib import Path
from typing import Optional, List
from collections import deque
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QProgressBar, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Signal, Slot, Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage
from PIL import Image
from ..processing.batch_queue import QueueItem, ItemStatus, QueueProgress, QueueStatus
from ..utils.i18n import tr
logger = logging.getLogger(__name__)
class ETACalculator:
    """Calculate ETA based on rolling average of processing times."""
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.times = deque(maxlen=window_size)
        self._last_start_time = None
    def start_item(self):
        """Mark the start of processing an item."""
        self._last_start_time = time.time()
    def complete_item(self):
        """Mark the completion of processing an item."""
        if self._last_start_time is not None:
            elapsed = time.time() - self._last_start_time
            self.times.append(elapsed)
            self._last_start_time = None
    def get_average_time(self) -> float:
        """Get the average processing time per item."""
        if not self.times:
            return 0
        return sum(self.times) / len(self.times)
    def get_eta(self, remaining_items: int) -> float:
        """Get estimated time remaining in seconds."""
        avg = self.get_average_time()
        return avg * remaining_items
    def get_items_per_minute(self) -> float:
        """Get processing rate in items per minute."""
        avg = self.get_average_time()
        if avg <= 0:
            return 0
        return 60 / avg
    def format_eta(self, remaining_items: int) -> str:
        """Format ETA as human-readable string."""
        eta_seconds = self.get_eta(remaining_items)
        if eta_seconds <= 0:
            return tr('Calculating...')
        if eta_seconds < 60:
            return f"~{int(eta_seconds)} {tr('sec remaining')}"
        if eta_seconds < 3600:
            minutes = int(eta_seconds / 60)
            return f"~{minutes} {tr('min remaining')}"
        hours = int(eta_seconds / 3600)
        minutes = int((eta_seconds % 3600) / 60)
        return f"~{hours}h {minutes}m {tr('remaining')}"
    def reset(self):
        """Reset the calculator."""
        self.times.clear()
        self._last_start_time = None
class BatchItemWidget(QWidget):
    """Thumbnail widget for a single batch item."""
    @staticmethod
    def _compact_text(text, max_len=18):
        text = str(text or '')
        if len(text) <= max_len:
            return text
        head = max(6, int(max_len * 0.55))
        tail = max(4, max_len - head - 1)
        return f'{text[:head]}…{text[-tail:]}'
    clicked = Signal(int)
    def __init__(self, item: QueueItem, parent=None, defer_thumbnail: bool = False):
        super().__init__(parent)
        self.item = item
        self._thumbnail_loaded = False
        self._setup_ui(defer_thumbnail)
    def _setup_ui(self, defer_thumbnail: bool):
        self.setFixedSize(80, 90)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(72, 54)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2f;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        if not defer_thumbnail:
            self._load_thumbnail()
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.status_label.setMinimumWidth(0)
        self.status_label.setMaximumWidth(72)
        self.status_label.setStyleSheet('font-size: 9px;')
        file_path = getattr(self.item, 'file_path', '')
        full_name = Path(str(file_path)).name if file_path else ''
        self.status_label.setText(self._compact_text(full_name, 18))
        self.status_label.setToolTip(full_name)
        layout.addWidget(self.status_label)
        self._update_style()
    def _load_thumbnail(self):
        """Load thumbnail from the item's image file."""
        try:
            if hasattr(self.item, 'file_path') and self.item.file_path:
                img = Image.open(self.item.file_path)
                img.thumbnail((64, 48))
                if img.mode == 'RGBA':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
                data = img.tobytes('raw', 'RGB' if img.mode == 'RGB' else 'RGBA')
                qimage = QImage(data, img.width, img.height,
                                img.width * (3 if img.mode == 'RGB' else 4),
                                QImage.Format_RGB888 if img.mode == 'RGB' else QImage.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)
                scaled = pixmap.scaled(64, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_label.setPixmap(scaled)
                self._thumbnail_loaded = True
        except Exception as e:
            logger.debug(f'Failed to load thumbnail: {e}')
    def _update_style(self):
        """Update widget style based on item status."""
        if hasattr(self.item, 'status'):
            if self.item.status == ItemStatus.PROCESSING:
                self.setStyleSheet('QWidget { border: 2px solid #4F46E5; }')
            elif self.item.status == ItemStatus.COMPLETED:
                self.setStyleSheet('QWidget { border: 2px solid #22c55e; }')
            elif self.item.status == ItemStatus.FAILED:
                self.setStyleSheet('QWidget { border: 2px solid #ef4444; }')
            else:
                self.setStyleSheet('QWidget { border: 2px solid transparent; }')
    def update_status(self, status: ItemStatus):
        """Update the displayed status."""
        if hasattr(self.item, 'status'):
            self.item.status = status
        self._update_style()
    def mousePressEvent(self, event):
        self.clicked.emit(self.item.index if hasattr(self.item, 'index') else 0)
        super().mousePressEvent(event)
class BatchQueuePanel(QWidget):
    """Panel for visualizing and controlling batch processing queue."""
    item_clicked = Signal(int)
    progress_updated = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._item_widgets = []
        self._eta_calculator = ETACalculator()
        self._start_time = None
        self._setup_ui()
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        # Progress section
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat('%v/%m')
        progress_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel(tr('Ready'))
        self.progress_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.progress_label.setMinimumWidth(0)
        self.progress_label.setWordWrap(True)
        self.progress_label.setStyleSheet('color: #a0a0a5; font-size: 11px;')
        progress_layout.addWidget(self.progress_label, 1)
        main_layout.addLayout(progress_layout)
        # Stats row
        stats_layout = QHBoxLayout()
        self.eta_label = QLabel('--')
        self.eta_label.setStyleSheet('color: #a0a0a5; font-size: 11px;')
        stats_layout.addWidget(self.eta_label)
        stats_layout.addStretch()
        self.rate_label = QLabel('')
        self.rate_label.setStyleSheet('color: #a0a0a5; font-size: 11px;')
        stats_layout.addWidget(self.rate_label)
        main_layout.addLayout(stats_layout)
        # Grid scroll area for thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(6)
        scroll.setWidget(self.grid_widget)
        main_layout.addWidget(scroll, 1)
        # Control buttons
        controls = QHBoxLayout()
        controls.addStretch()
        self.cancel_btn = QPushButton(tr('Cancel All'))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        controls.addWidget(self.cancel_btn)
        main_layout.addLayout(controls)
    def add_items(self, items: List[QueueItem]):
        """Add items to the queue panel."""
        self._items = items
        self._rebuild_grid()
    def _rebuild_grid(self):
        """Rebuild the grid of item widgets."""
        for w in self._item_widgets:
            w.deleteLater()
        self._item_widgets.clear()
        columns = 4
        for i, item in enumerate(self._items):
            widget = BatchItemWidget(item, defer_thumbnail=(i > 20))
            widget.clicked.connect(self.item_clicked.emit)
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(widget, row, col)
            self._item_widgets.append(widget)
    def update_progress(self, progress: QueueProgress):
        """Update progress display."""
        total = progress.total
        completed = progress.completed
        failed = progress.failed
        if total > 0:
            pct = int((completed + failed) / total * 100)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(completed + failed)
            self.progress_bar.setFormat(f'{completed + failed}/{total}')
        remaining = total - completed - failed
        self.progress_label.setText(
            f"{tr('Completed')}: {completed} | {tr('Failed')}: {failed} | {tr('Remaining')}: {remaining}"
        )
        eta = self._eta_calculator.format_eta(remaining)
        self.eta_label.setText(f"{tr('ETA')}: {eta}")
        rate = self._eta_calculator.get_items_per_minute()
        if rate > 0:
            self.rate_label.setText(f"{rate:.1f} {tr('items/min')}")
        self.progress_updated.emit(progress)
        # Update individual item widgets
        for widget in self._item_widgets:
            widget._update_style()
    def _on_cancel(self):
        """Handle cancel button click."""
        logger.info('Batch processing cancelled by user')
    def reset(self):
        """Reset the panel for a new batch."""
        self._items.clear()
        for w in self._item_widgets:
            w.deleteLater()
        self._item_widgets.clear()
        self._eta_calculator.reset()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('0/0')
        self.progress_label.setText(tr('Ready'))
        self.eta_label.setText('--')
        self.rate_label.setText('')
        self._start_time = None
