'''
Welcome Screen
==============
Initial upload screen with drag-drop.
'''
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QSizePolicy
from PySide6.QtCore import Signal, Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
from ..utils.i18n import tr
class DropZone(QFrame):
    '''Drag and drop zone for images.'''
    files_dropped = Signal(list)
    clicked = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(500, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._setup_ui()
    def _setup_ui(self):
        self.setStyleSheet('\n            DropZone {\n                background-color: #1a1a1d;\n                border: 3px dashed #3a3a40;\n                border-radius: 16px;\n            }\n            DropZone:hover {\n                border-color: #4F46E5;\n                background-color: rgba(79, 70, 229, 0.05);\n            }\n        ')
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        icon_label = QLabel('🖼️')
        icon_label.setStyleSheet('font-size: 64px; background: transparent; border: none;')
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        self.title_label = QLabel(tr('Drop your images here'))
        self.title_label.setStyleSheet('\n            font-size: 24px;\n            font-weight: bold;\n            color: #ffffff;\n            background: transparent;\n            border: none;\n        ')
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        self.subtitle_label = QLabel(tr('or click to browse • PNG, JPG, WebP supported'))
        self.subtitle_label.setStyleSheet('\n            font-size: 14px;\n            color: #a0a0a5;\n            background: transparent;\n            border: none;\n        ')
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)
        self.batch_tip_label = QLabel(tr('Select multiple files for batch processing'))
        self.batch_tip_label.setStyleSheet('\n            font-size: 13px;\n            color: #4F46E5;\n            font-weight: bold;\n            background: transparent;\n            border: none;\n        ')
        self.batch_tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.batch_tip_label)
        self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            return None
    def dragEnterEvent(self, event = None):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet('\n                DropZone {\n                    background-color: rgba(79, 70, 229, 0.1);\n                    border: 3px dashed #4F46E5;\n                    border-radius: 16px;\n                }\n            ')
            return None
    def _reset_style(self):
        '''Reset the drop zone style back to default (without recreating children).'''
        self.setStyleSheet('\n            DropZone {\n                background-color: #1a1a1d;\n                border: 3px dashed #3a3a40;\n                border-radius: 16px;\n            }\n            DropZone:hover {\n                border-color: #4F46E5;\n                background-color: rgba(79, 70, 229, 0.05);\n            }\n        ')
    def dragLeaveEvent(self, event):
        self._reset_style()
    def dropEvent(self, event = None):
        self._reset_style()
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            p = Path(path)
            if p.is_dir():
                files.extend(str(f) for f in p.rglob('*') if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'))
            elif p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'):
                files.append(str(p))
        if files:
            self.files_dropped.emit(files)
            return None
class WelcomeScreen(QWidget):
    '''Welcome screen with upload area.'''
    files_selected = Signal(list)
    def __init__(self, parent = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(32)
        layout.setAlignment(Qt.AlignCenter)
        self.header_label = QLabel('QuestCut-AI')
        self.header_label.setStyleSheet('\n            font-size: 32px;\n            font-weight: bold;\n            color: #ffffff;\n        ')
        self.header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.header_label)
        self.tagline_label = QLabel(tr('Unlimited. Offline. Yours forever.'))
        self.tagline_label.setStyleSheet('\n            font-size: 16px;\n            color: #a0a0a5;\n        ')
        self.tagline_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tagline_label)
        layout.addSpacing(20)
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone, 1)
        layout.addSpacing(20)
        layout.addSpacing(16)
        batch_info = QFrame()
        batch_info.setStyleSheet('\n            QFrame {\n                background: rgba(79, 70, 229, 0.05);\n                border: 1px solid rgba(79, 70, 229, 0.2);\n                border-radius: 8px;\n                padding: 12px;\n            }\n        ')
        batch_layout = QHBoxLayout(batch_info)
        batch_layout.setContentsMargins(16, 8, 16, 8)
        batch_icon = QLabel('📁')
        batch_icon.setStyleSheet('font-size: 20px; background: transparent; border: none;')
        batch_layout.addWidget(batch_icon)
        self.batch_text_label = QLabel("<b style='color: #ffffff;'>Batch Processing:</b> <span style='color: #a0a0a5;'>Drop a folder or select 2+ images to process them all at once with automatic saving</span>")
        self.batch_text_label.setStyleSheet('background: transparent; border: none;')
        self.batch_text_label.setWordWrap(True)
        batch_layout.addWidget(self.batch_text_label, 1)
        layout.addWidget(batch_info)
        layout.addSpacing(12)
        self.footer_label = QLabel(tr('100% offline • Images never leave your computer • Unlimited processing'))
        self.footer_label.setStyleSheet('\n            font-size: 12px;\n            color: #606065;\n        ')
        self.footer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.footer_label)
    def _connect_signals(self):
        self.drop_zone.files_dropped.connect(self.files_selected.emit)
        self.drop_zone.clicked.connect(self._browse_files)
    def _browse_files(self):
        '''Open file browser.'''
        (files, _) = QFileDialog.getOpenFileNames(self, tr('Select Images'), '', tr('Images (*.png *.jpg *.jpeg *.webp *.bmp)'))
        if files:
            self.files_selected.emit(files)
            return None


def _dropzone_retranslate(self):
    self.title_label.setText(tr('Drop your images here'))
    self.subtitle_label.setText(tr('or click to browse • PNG, JPG, WebP supported'))
    self.batch_tip_label.setText(tr('Select multiple files for batch processing'))

DropZone.retranslate_ui = _dropzone_retranslate

def _welcome_retranslate(self):
    self.tagline_label.setText(tr('Unlimited. Offline. Yours forever.'))
    self.batch_text_label.setText(
        f"<b style='color: #ffffff;'>{tr('Batch Processing:')}</b> "
        f"<span style='color: #a0a0a5;'>{tr('Drop a folder or select 2+ images to process them all at once with automatic saving')}</span>"
    )
    self.footer_label.setText(tr('100% offline • Images never leave your computer • Unlimited processing'))
    self.drop_zone.retranslate_ui()

WelcomeScreen.retranslate_ui = _welcome_retranslate
