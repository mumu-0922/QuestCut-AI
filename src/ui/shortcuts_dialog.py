'''
Keyboard Shortcuts Dialog
========================
Displays all available keyboard shortcuts in a beautiful overlay.
'''
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QWidget, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..utils.i18n import tr
class ShortcutsDialog(QDialog):
    '''Beautiful keyboard shortcuts overlay dialog.'''
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle(tr('Keyboard Shortcuts'))
        self.setModal(True)
        self.setFixedSize(500, 550)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_ui()
    def _setup_ui(self):
        '''Setup the dialog UI.'''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QFrame()
        container.setStyleSheet('\n            QFrame {\n                background-color: #1a1a1d;\n                border: 1px solid #3a3a40;\n                border-radius: 16px;\n            }\n        ')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)
        header_layout = QHBoxLayout()
        title = QLabel(tr('Keyboard Shortcuts'))
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #ffffff;')
        header_layout.addWidget(title)
        header_layout.addStretch()
        close_btn = QPushButton('×')
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: none;\n                border-radius: 16px;\n                color: #a0a0a5;\n                font-size: 20px;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #ef4444;\n                color: white;\n            }\n        ')
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        sections = [
            (tr('File'), [
                ('Ctrl+O', tr('Open image')),
                ('Ctrl+S', tr('Save image')),
                ('Ctrl+Shift+S', tr('Save as...'))]),
            (tr('View'), [
                ('Space', tr('Toggle original/result')),
                ('C', tr('Enable comparison slider')),
                ('+ / -', tr('Zoom in/out')),
                ('0', tr('Fit to view')),
                ('1', tr('Zoom to 100%'))]),
            (tr('Edit'), [
                ('Ctrl+Z', tr('Undo')),
                ('Ctrl+Y', tr('Redo')),
                ('[ / ]', tr('Decrease/increase brush size'))]),
            (tr('Tools'), [
                ('B', tr('Brush tool')),
                ('H', tr('Pan/hand tool'))])]
        for section_title, shortcuts in sections:
            section = self._create_section(section_title, shortcuts)
            container_layout.addWidget(section)
        hint = QLabel(tr('Press Esc or ? to close'))
        hint.setStyleSheet('color: #606065; font-size: 11px;')
        hint.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(hint)
        layout.addWidget(container)
    def _create_section(self, title = None, shortcuts = None):
        '''Create a shortcut section.'''
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setStyleSheet('color: #4F46E5; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;')
        layout.addWidget(title_label)
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, description) in enumerate(shortcuts):
            key_label = QLabel(key)
            key_label.setFixedWidth(100)
            key_label.setStyleSheet("\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                padding: 4px 8px;\n                color: #ffffff;\n                font-family: 'Consolas', 'Monaco', monospace;\n                font-size: 12px;\n            ")
            key_label.setAlignment(Qt.AlignCenter)
            grid.addWidget(key_label, i, 0)
            desc_label = QLabel(description)
            desc_label.setStyleSheet('color: #a0a0a5; font-size: 13px;')
            grid.addWidget(desc_label, i, 1)
        layout.addLayout(grid)
        return section
    def keyPressEvent(self, event = None):
        '''Close on Escape or ?'''
        if event.key() in (Qt.Key_Escape, Qt.Key_Question):
            self.close()
            return None
        super().keyPressEvent(event)
    @staticmethod
    def show_shortcuts(parent=None):
        '''Show the shortcuts dialog.'''
        dialog = ShortcutsDialog(parent)
        dialog.exec()
