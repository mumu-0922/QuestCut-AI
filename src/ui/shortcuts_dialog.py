'''
Keyboard Shortcuts Dialog
========================
Displays available keyboard shortcuts in a clear overlay.
'''
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton, QSizePolicy
from PySide6.QtCore import Qt
from ..utils.i18n import tr


class ShortcutsDialog(QDialog):
    '''Keyboard shortcuts overlay dialog.'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Keyboard Shortcuts'))
        self.setModal(True)
        self.setMinimumSize(900, 560)
        self.resize(960, 600)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        '''Setup the dialog UI.'''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName('shortcutsContainer')
        container.setStyleSheet('''
            QFrame#shortcutsContainer {
                background-color: #1a1a1d;
                border: 1px solid #3a3a40;
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        ''')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(34, 30, 34, 28)
        container_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title = QLabel(tr('Keyboard Shortcuts'))
        title.setStyleSheet('font-size: 26px; font-weight: bold; color: #ffffff;')
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton('×')
        close_btn.setFixedSize(44, 44)
        close_btn.setStyleSheet('''
            QPushButton {
                background-color: #2a2a2f;
                border: none;
                border-radius: 22px;
                color: #a0a0a5;
                font-size: 26px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        ''')
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)

        columns = [
            [
                (tr('File'), [
                    ('Ctrl+O', tr('Open image')),
                    ('Ctrl+S', tr('Save image')),
                    ('Ctrl+Shift+S', tr('Save as...')),
                ]),
                (tr('Edit'), [
                    ('Ctrl+Z', tr('Undo')),
                    ('Ctrl+Y', tr('Redo')),
                    ('[ / ]', tr('Decrease/increase brush size')),
                ]),
            ],
            [
                (tr('View'), [
                    ('Space', tr('Toggle original/result')),
                    ('C', tr('Enable comparison slider')),
                    ('+ / -', tr('Zoom in/out')),
                    ('0', tr('Fit to view')),
                    ('1', tr('Zoom to 100%')),
                ]),
                (tr('Tools'), [
                    ('B', tr('Brush tool')),
                    ('H', tr('Pan/hand tool')),
                ]),
            ],
        ]
        columns_widget = QWidget()
        columns_layout = QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(22)
        for column_sections in columns:
            column = QWidget()
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(16)
            for section_title, shortcuts in column_sections:
                column_layout.addWidget(self._create_section(section_title, shortcuts))
            column_layout.addStretch(1)
            columns_layout.addWidget(column, 1)
        container_layout.addWidget(columns_widget, 1)

        hint = QLabel(tr('Press Esc or ? to close'))
        hint.setStyleSheet('color: #606065; font-size: 13px; padding-top: 4px;')
        hint.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(hint)
        layout.addWidget(container)

    def _create_section(self, title=None, shortcuts=None):
        '''Create a shortcut section with fixed-height rows.'''
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setFixedHeight(34)
        title_label.setStyleSheet('''
            color: #6366f1;
            font-size: 16px;
            font-weight: bold;
            padding: 2px 6px;
            border: 1px solid #3a3a40;
            border-radius: 2px;
        ''')
        layout.addWidget(title_label)

        for key, description in shortcuts or []:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            key_label = QLabel(key)
            key_label.setFixedSize(142, 38)
            key_label.setAlignment(Qt.AlignCenter)
            key_label.setStyleSheet('''
                background-color: #2a2a2f;
                border: 1px solid #3a3a40;
                border-radius: 5px;
                color: #ffffff;
                font-family: Consolas, Monaco, monospace;
                font-size: 15px;
                font-weight: 600;
            ''')
            row_layout.addWidget(key_label)

            desc_label = QLabel(description)
            desc_label.setFixedHeight(38)
            desc_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            desc_label.setStyleSheet('''
                color: #c7c7d1;
                font-size: 16px;
                padding: 5px 10px;
                border: 1px solid #3a3a40;
                border-radius: 2px;
            ''')
            row_layout.addWidget(desc_label, 1)
            layout.addWidget(row)
        return section

    def keyPressEvent(self, event=None):
        '''Close on Escape or ?.'''
        if event.key() in (Qt.Key_Escape, Qt.Key_Question) or event.text() in ('?', '？'):
            self.close()
            return None
        super().keyPressEvent(event)

    @staticmethod
    def show_shortcuts(parent=None):
        '''Show the shortcuts dialog.'''
        dialog = ShortcutsDialog(parent)
        dialog.exec()
