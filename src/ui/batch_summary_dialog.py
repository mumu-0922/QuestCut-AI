'''
Batch Summary Dialog
====================
Shown when batch processing completes with statistics, failed items, and actions.
'''
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QWidget, QPushButton, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, Signal
from ..processing.batch_queue import QueueProgress, QueueStatus
from ..utils.i18n import tr
class BatchSummaryDialog(QDialog):
    '''End-of-batch summary dialog.'''
    retry_failed = Signal()
    open_folder = Signal()
    process_more = Signal()
    def __init__(self, progress = None, batch_images = None, output_dir = None, elapsed_time = None, save_stats = None, parent = None):
        super().__init__(parent)
        self._progress = progress
        self._batch_images = batch_images
        self._output_dir = output_dir
        self._elapsed_time = elapsed_time
        self._save_stats = save_stats
        self.setWindowTitle(tr('Batch Complete'))
        self.setModal(True)
        self.setFixedSize(500, 520)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_ui()
    @staticmethod
    def _compact_text(text, max_len=96):
        text = str(text or '')
        if len(text) <= max_len:
            return text
        head = max(18, int(max_len * 0.55))
        tail = max(14, max_len - head - 1)
        return f'{text[:head]}…{text[-tail:]}'
    def _make_safe_label(self, text='', *, color='#a0a0a5', max_width=430, max_len=96):
        full_text = str(text or '')
        label = QLabel(self._compact_text(full_text, max_len))
        label.setToolTip(full_text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setMinimumWidth(0)
        label.setMaximumWidth(max_width)
        label.setStyleSheet(f'color: {color}; font-size: 11px; background: transparent;')
        return label
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QFrame()
        container.setStyleSheet('\n            QFrame {\n                background-color: #1a1a1d;\n                border: 1px solid #3a3a40;\n                border-radius: 16px;\n            }\n        ')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)
        header_layout = QHBoxLayout()
        is_cancelled = getattr(self._progress, 'status', QueueStatus.IDLE) == QueueStatus.CANCELLED
        has_failures = self._progress.failed > 0
        if is_cancelled:
            header_text = tr('Batch Cancelled')
            header_color = '#f59e0b'
        elif has_failures:
            header_text = tr('Batch Complete (with errors)')
            header_color = '#f59e0b'
        else:
            header_text = tr('Batch Complete!')
            header_color = '#22c55e'
        title = QLabel(header_text)
        title.setStyleSheet(f'''font-size: 20px; font-weight: bold; color: {header_color}; background: transparent;''')
        header_layout.addWidget(title)
        header_layout.addStretch()
        close_btn = QPushButton('×')
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: none;\n                border-radius: 16px;\n                color: #a0a0a5;\n                font-size: 20px;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #ef4444;\n                color: white;\n            }\n        ')
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        stats_frame = QFrame()
        stats_frame.setStyleSheet('\n            QFrame {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 8px;\n            }\n        ')
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(8)
        row = 0
        self._add_stat_row(stats_layout, row, tr('Total Images'), str(self._progress.total), '#ffffff')
        row += 1
        self._add_stat_row(stats_layout, row, tr('Succeeded'), str(self._progress.completed), '#22c55e')
        row += 1
        if self._progress.failed > 0:
            self._add_stat_row(stats_layout, row, tr('Failed'), str(self._progress.failed), '#ef4444')
            row += 1
        if self._progress.skipped > 0:
            self._add_stat_row(stats_layout, row, tr('Skipped'), str(self._progress.skipped), '#f59e0b')
            row += 1
        self._add_stat_row(stats_layout, row, tr('Total Time'), self._format_duration(self._elapsed_time), '#a0a0a5')
        row += 1
        if self._elapsed_time > 0 and self._progress.completed > 0:
            speed = self._progress.completed / self._elapsed_time / 60
            self._add_stat_row(stats_layout, row, tr('Speed'), f'''{speed:.1f} {tr('images/min')}''', '#a0a0a5')
            row += 1
        if self._save_stats:
            saved = self._save_stats.get('saved_count', 0)
            total_mb = self._save_stats.get('total_mb', 0)
            self._add_stat_row(stats_layout, row, tr('Files Saved'), str(saved), '#22c55e')
            row += 1
            if total_mb > 0:
                self._add_stat_row(stats_layout, row, tr('Total Size'), f'''{total_mb:.1f} MB''', '#a0a0a5')
                row += 1
        container_layout.addWidget(stats_frame)
        if self._progress.failed > 0:
            failed_label = self._create_section_label(tr('FAILED ITEMS'))
            container_layout.addWidget(failed_label)
            scroll = QScrollArea()
            scroll.setMaximumHeight(120)
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet('\n                QScrollArea {\n                    background-color: rgba(239, 68, 68, 0.05);\n                    border: 1px solid rgba(239, 68, 68, 0.2);\n                    border-radius: 6px;\n                }\n                QScrollBar:vertical {\n                    width: 6px;\n                    background: transparent;\n                }\n                QScrollBar::handle:vertical {\n                    background: #3a3a40;\n                    border-radius: 3px;\n                }\n            ')
            failed_widget = QWidget()
            failed_widget.setStyleSheet('background: transparent;')
            failed_layout = QVBoxLayout(failed_widget)
            failed_layout.setContentsMargins(8, 8, 8, 8)
            failed_layout.setSpacing(4)
            failed_images = [img for img in self._batch_images if img.has_error]
            for img in failed_images:
                full_error = f'''{img.filename}: {img.error_message}'''
                item_label = self._make_safe_label(full_error, color='#ef4444', max_width=430, max_len=120)
                failed_layout.addWidget(item_label)
            failed_layout.addStretch()
            scroll.setWidget(failed_widget)
            container_layout.addWidget(scroll)
            retry_btn = QPushButton(tr('Retry Failed'))
            retry_btn.setFixedHeight(36)
            retry_btn.setStyleSheet(self._secondary_btn_style(True))
            retry_btn.clicked.connect(self._on_retry)
            container_layout.addWidget(retry_btn)
        if self._output_dir:
            dir_frame = QFrame()
            dir_frame.setStyleSheet('\n                QFrame {\n                    background-color: #2a2a2f;\n                    border: 1px solid #3a3a40;\n                    border-radius: 8px;\n                }\n            ')
            dir_layout = QHBoxLayout(dir_frame)
            dir_layout.setContentsMargins(12, 8, 12, 8)
            dir_layout.setSpacing(8)
            dir_label = self._make_safe_label(self._output_dir, color='#a0a0a5', max_width=340, max_len=86)
            dir_layout.addWidget(dir_label, 1)
            open_btn = QPushButton(tr('Open Folder'))
            open_btn.setFixedHeight(32)
            open_btn.setStyleSheet(self._secondary_btn_style())
            open_btn.clicked.connect(self._on_open_folder)
            dir_layout.addWidget(open_btn)
            container_layout.addWidget(dir_frame)
        container_layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        close_action_btn = QPushButton(tr('Close'))
        close_action_btn.setFixedHeight(44)
        close_action_btn.setStyleSheet(self._secondary_btn_style())
        close_action_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_action_btn)
        more_btn = QPushButton(tr('Process More'))
        more_btn.setFixedHeight(44)
        more_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 8px;\n                color: white;\n                font-size: 14px;\n                font-weight: bold;\n                padding: 0 32px;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n            QPushButton:pressed {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #3730A3, stop:1 #5B21B6);\n            }\n        ')
        more_btn.clicked.connect(self._on_process_more)
        btn_layout.addWidget(more_btn, 1)
        container_layout.addLayout(btn_layout)
        layout.addWidget(container)
    def _add_stat_row(self, grid: QGridLayout, row: int, label_text: str, value_text: str, value_color: str = '#ffffff'):
        label = QLabel(label_text)
        label.setStyleSheet('color: #a0a0a5; font-size: 13px; background: transparent;')
        grid.addWidget(label, row, 0)
        value = QLabel(self._compact_text(value_text, 48))
        value.setToolTip(value_text)
        value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        value.setMinimumWidth(0)
        value.setStyleSheet(f'''color: {value_color}; font-size: 13px; font-weight: bold; background: transparent;''')
        value.setAlignment(Qt.AlignRight)
        grid.addWidget(value, row, 1)
    def _create_section_label(self, text = None):
        label = QLabel(text)
        label.setStyleSheet('color: #4F46E5; font-size: 10px; font-weight: bold; letter-spacing: 1px; background: transparent;')
        return label
    def _format_duration(self, seconds = None):
        if seconds < 60:
            return f'''{seconds:.0f}s'''
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f'''{minutes}m {secs}s'''
        hours = int(minutes // 60)
        mins = minutes % 60
        return f'''{hours}h {mins}m'''
    def _secondary_btn_style(self, accent = None):
        border_color = '#4F46E5' if accent else '#3a3a40'
        text_color = '#ffffff' if accent else '#a0a0a5'
        return f'''\n            QPushButton {{\n                background-color: transparent;\n                border: 1px solid {border_color};\n                border-radius: 6px;\n                padding: 8px 16px;\n                color: {text_color};\n                font-size: 13px;\n            }}\n            QPushButton:hover {{\n                border-color: #4F46E5;\n                color: #ffffff;\n            }}\n        '''
    def _on_retry(self):
        self.retry_failed.emit()
        self.accept()
    def _on_open_folder(self):
        self.open_folder.emit()
    def _on_process_more(self):
        self.process_more.emit()
        self.accept()
    def keyPressEvent(self, event = None):
        if event.key() == Qt.Key_Escape:
            self.accept()
            return None
        super().keyPressEvent(event)
