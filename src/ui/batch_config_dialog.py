"""
Batch Configuration Dialog
==========================
Pre-batch configuration dialog shown before processing begins.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
)

from ..utils.constants import EXPORT_FORMATS, MODEL_CONFIG, MODEL_DISPLAY_ORDER
from ..utils.i18n import tr, tr_model_display


@dataclass
class BatchConfig:
    output_dir: str = ''
    model_key: str = ''
    export_format: str = 'png'
    quality: int = 90
    naming_template: str = '{original}_nobg'
    auto_save: bool = False


class BatchConfigDialog(QDialog):
    """Pre-batch configuration dialog."""

    _AUTO_SAVE_THRESHOLD = 50

    def __init__(self, files=None, current_model=None, parent=None):
        super().__init__(parent)
        self._files = list(files or [])
        self._current_model = current_model or 'birefnet'
        self._config = None
        self._default_output_dir = str(Path(self._files[0]).parent) if self._files else str(Path.home())
        self.setWindowTitle(tr('Batch Configuration'))
        self.setModal(True)
        self.setMinimumSize(560, 560)
        self._setup_ui()

    @staticmethod
    def _compact_text(text, max_len=72):
        text = str(text or '')
        if len(text) <= max_len:
            return text
        head = max(16, int(max_len * 0.55))
        tail = max(12, max_len - head - 1)
        return f'{text[:head]}…{text[-tail:]}'

    def _make_wrapped_label(self, text='', *, max_width=500, max_len=90):
        full_text = str(text or '')
        label = QLabel(self._compact_text(full_text, max_len))
        label.setToolTip(full_text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setMinimumWidth(0)
        label.setMaximumWidth(max_width)
        return label

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        container = QFrame()
        container.setStyleSheet('''
            QFrame { background-color: #1a1a1d; border: 1px solid #3a3a40; border-radius: 16px; }
            QLabel { color: #ffffff; background: transparent; border: none; }
        ''')
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(tr('Batch Configuration'))
        title.setStyleSheet('font-size: 20px; font-weight: bold;')
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton('×')
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(self._secondary_btn_style(True))
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)

        file_frame = self._create_section_frame()
        file_layout = QVBoxLayout(file_frame)
        file_layout.setContentsMargins(12, 12, 12, 12)
        count_label = QLabel(f"{len(self._files)} {tr('images')} {tr('selected')}")
        count_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        file_layout.addWidget(count_label)
        preview_names = [Path(f).name for f in self._files[:4]]
        if len(self._files) > 4:
            preview_names.append(f"...{tr('and')} {len(self._files) - 4} {tr('more')}")
        names_full_text = '\n'.join(preview_names)
        self.names_label = self._make_wrapped_label(names_full_text, max_width=480, max_len=150)
        self.names_label.setStyleSheet('font-size: 11px; color: #a0a0a5;')
        file_layout.addWidget(self.names_label)
        layout.addWidget(file_frame)

        layout.addWidget(self._create_section_label(tr('OUTPUT DIRECTORY')))
        dir_row = QHBoxLayout()
        self.output_dir_input = QLineEdit(self._default_output_dir)
        self.output_dir_input.setToolTip(self._default_output_dir)
        self.output_dir_input.setMinimumWidth(0)
        self.output_dir_input.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.output_dir_input.setStyleSheet(self._input_style())
        dir_row.addWidget(self.output_dir_input, 1)
        browse_btn = QPushButton(tr('Browse...'))
        browse_btn.setFixedHeight(36)
        browse_btn.setStyleSheet(self._secondary_btn_style())
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        layout.addWidget(self._create_section_label(tr('AI MODEL')))
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(self._combo_style())
        self.model_combo.setFixedHeight(36)
        for key in MODEL_DISPLAY_ORDER:
            config = MODEL_CONFIG.get(key, {})
            display = tr_model_display(key, config.get('display_name', key))
            size = config.get('size', '')
            self.model_combo.addItem(f'{display}  {size}', key)
        idx = self.model_combo.findData(self._current_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        layout.addWidget(self.model_combo)

        format_row = QHBoxLayout()
        format_col = QVBoxLayout()
        format_col.addWidget(self._create_section_label(tr('FORMAT')))
        self.format_combo = QComboBox()
        self.format_combo.setStyleSheet(self._combo_style())
        self.format_combo.setFixedHeight(36)
        for key, fmt in EXPORT_FORMATS.items():
            self.format_combo.addItem(fmt['name'], key)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        format_col.addWidget(self.format_combo)
        format_row.addLayout(format_col, 1)

        quality_col = QVBoxLayout()
        self.quality_section_label = self._create_section_label(f"{tr('QUALITY')}: 90%")
        quality_col.addWidget(self.quality_section_label)
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_col.addWidget(self.quality_slider)
        format_row.addLayout(quality_col, 1)
        layout.addLayout(format_row)
        self._on_format_changed()

        layout.addWidget(self._create_section_label(tr('NAMING TEMPLATE')))
        self.naming_input = QLineEdit('{original}_nobg')
        self.naming_input.setStyleSheet(self._input_style())
        self.naming_input.textChanged.connect(self._update_preview)
        layout.addWidget(self.naming_input)
        self.preview_label = self._make_wrapped_label('', max_width=500, max_len=110)
        self.preview_label.setStyleSheet('font-size: 11px; color: #606065;')
        layout.addWidget(self.preview_label)
        self._update_preview()

        auto_save_frame = self._create_section_frame(True)
        auto_layout = QVBoxLayout(auto_save_frame)
        auto_layout.setContentsMargins(12, 12, 12, 12)
        self.auto_save_check = QCheckBox(tr('Auto-save (fire-and-forget mode)'))
        self.auto_save_check.setChecked(len(self._files) >= self._AUTO_SAVE_THRESHOLD)
        self.auto_save_check.setStyleSheet('color: #ffffff; font-size: 13px; font-weight: bold; background: transparent;')
        auto_layout.addWidget(self.auto_save_check)
        desc = QLabel(tr('Save each image immediately after processing and release memory. Best for large batches.'))
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 11px; color: #a0a0a5;')
        auto_layout.addWidget(desc)
        self._auto_save_warning = QLabel(f"⚠ {tr('With')} {len(self._files)} {tr('images')}, {tr('disabling auto-save keeps all results in memory.')}")
        self._auto_save_warning.setWordWrap(True)
        self._auto_save_warning.setStyleSheet('font-size: 11px; color: #f59e0b;')
        self._auto_save_warning.setVisible(False)
        auto_layout.addWidget(self._auto_save_warning)
        self.auto_save_check.toggled.connect(self._on_auto_save_toggled)
        self._on_auto_save_toggled(self.auto_save_check.isChecked())
        layout.addWidget(auto_save_frame)

        layout.addStretch()
        buttons = QHBoxLayout()
        cancel_btn = QPushButton(tr('Cancel'))
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet(self._secondary_btn_style())
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        start_btn = QPushButton(tr('Start Processing'))
        start_btn.setFixedHeight(44)
        start_btn.setStyleSheet('''
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); border: none; border-radius: 8px; color: white; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); }
        ''')
        start_btn.clicked.connect(self._on_start)
        buttons.addWidget(start_btn, 1)
        layout.addLayout(buttons)

        root.addWidget(container)

    def _create_section_label(self, text=None):
        label = QLabel(text)
        label.setStyleSheet('color: #4F46E5; font-size: 10px; font-weight: bold; letter-spacing: 1px; background: transparent; border: none;')
        return label

    def _create_section_frame(self, accent=None):
        frame = QFrame()
        if accent:
            frame.setStyleSheet('QFrame { background-color: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.2); border-radius: 8px; }')
        else:
            frame.setStyleSheet('QFrame { background-color: #2a2a2f; border: 1px solid #3a3a40; border-radius: 8px; }')
        return frame

    def _input_style(self):
        return 'QLineEdit { background-color: #2a2a2f; border: 1px solid #3a3a40; border-radius: 6px; padding: 6px 12px; color: #ffffff; font-size: 13px; } QLineEdit:focus { border-color: #4F46E5; }'

    def _combo_style(self):
        return 'QComboBox { background-color: #2a2a2f; border: 1px solid #3a3a40; border-radius: 6px; padding: 6px 12px; color: #ffffff; font-size: 13px; } QComboBox:focus { border-color: #4F46E5; } QComboBox QAbstractItemView { background-color: #2a2a2f; border: 1px solid #3a3a40; color: #ffffff; selection-background-color: #4F46E5; }'

    def _secondary_btn_style(self, danger=None):
        hover = '#ef4444' if danger else '#4F46E5'
        return f'QPushButton {{ background-color: transparent; border: 1px solid #3a3a40; border-radius: 6px; padding: 8px 16px; color: #a0a0a5; font-size: 13px; }} QPushButton:hover {{ border-color: {hover}; color: #ffffff; }} QPushButton:disabled {{ color: #3a3a40; border-color: #2a2a2f; }}'

    def _on_auto_save_toggled(self, checked=None):
        self._auto_save_warning.setVisible(len(self._files) >= self._AUTO_SAVE_THRESHOLD and not checked)

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, tr('Select Output Directory'), self.output_dir_input.text(), QFileDialog.ShowDirsOnly)
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self.output_dir_input.setToolTip(dir_path)

    def _on_format_changed(self):
        fmt_key = self.format_combo.currentData() or 'png'
        supports_quality = EXPORT_FORMATS.get(fmt_key, {}).get('supports_quality', False)
        self.quality_slider.setVisible(supports_quality)
        self.quality_section_label.setVisible(supports_quality)
        self._update_preview()

    def _on_quality_changed(self, value=None):
        self.quality_section_label.setText(f"{tr('QUALITY')}: {value}%")

    def _update_preview(self):
        if not hasattr(self, 'preview_label'):
            return
        first = Path(self._files[0]).stem if self._files else 'image'
        template = self.naming_input.text().strip() if hasattr(self, 'naming_input') else '{original}_nobg'
        fmt_key = self.format_combo.currentData() if hasattr(self, 'format_combo') else 'png'
        ext = EXPORT_FORMATS.get(fmt_key or 'png', {}).get('extension', '.png')
        name = (template or '{original}_nobg').replace('{original}', first)
        preview = f"{tr('Preview:')} {name}{ext}"
        self.preview_label.setText(self._compact_text(preview, 110))
        self.preview_label.setToolTip(preview)

    def _validate(self):
        output_dir = self.output_dir_input.text().strip()
        if not output_dir:
            QMessageBox.warning(self, tr('Missing Output Directory'), tr('Please select an output directory.'))
            return False
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.warning(self, tr('Invalid Output Directory'), f"{tr('Could not create output directory:')}\n{exc}")
            return False
        if not self.naming_input.text().strip():
            QMessageBox.warning(self, tr('Missing Naming Template'), tr('Please enter a naming template, e.g. {original}_nobg.'))
            return False
        return True

    def _on_start(self):
        if not self._validate():
            return
        self._config = BatchConfig(
            output_dir=self.output_dir_input.text().strip(),
            model_key=self.model_combo.currentData() or 'birefnet',
            export_format=self.format_combo.currentData() or 'png',
            quality=self.quality_slider.value(),
            naming_template=self.naming_input.text().strip(),
            auto_save=self.auto_save_check.isChecked(),
        )
        self.accept()

    def get_config(self):
        return self._config

    def keyPressEvent(self, event=None):
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    @staticmethod
    def configure_batch(files=None, current_model=None, parent=None):
        """Show the batch config dialog and return config or None."""
        dialog = BatchConfigDialog(files, current_model, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.get_config()
        return None
