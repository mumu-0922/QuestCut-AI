'''
Control Panel for QuestCut-AI
=========================
Settings panels for background, shadow, export, etc.
'''
import logging
from typing import Optional, Tuple, Dict, Any, List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QLabel, QSlider, QComboBox, QSpinBox, QCheckBox, QLineEdit, QColorDialog, QFileDialog, QFrame, QGroupBox, QButtonGroup, QGridLayout, QSizePolicy, QProgressBar
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer
from PySide6.QtGui import QColor, QPalette
from ..resources.icons import get_icon
from PIL import Image
from ..utils.constants import GRADIENT_PRESETS, SHADOW_PRESETS, PLATFORM_SIZES, PLATFORM_CATEGORIES, EXPORT_FORMATS, COLORS, MODEL_CONFIG, MODEL_DISPLAY_ORDER, DEFAULT_SETTINGS
from ..utils.i18n import LANGUAGES, get_language, set_language, tr, tr_model_display, tr_model_description
from ..processing.shadow import ShadowSettings
from ..processing.export import ExportSettings
from .styles import GPU_STATUS_BASE, STATUS_ERROR, STATUS_NEUTRAL, STATUS_SUCCESS
logger = logging.getLogger(__name__)
class NoWheelSlider(QSlider):
    '''QSlider that ignores wheel events unless explicitly focused.'''
    def wheelEvent(self, event = None):
        if self.hasFocus():
            super().wheelEvent(event)
            return None
        event.ignore()
class NoWheelComboBox(QComboBox):
    '''QComboBox that ignores wheel events unless explicitly focused.'''
    def wheelEvent(self, event = None):
        if self.hasFocus():
            super().wheelEvent(event)
            return None
        event.ignore()
class NoWheelSpinBox(QSpinBox):
    '''QSpinBox that ignores wheel events unless explicitly focused.'''
    def wheelEvent(self, event = None):
        if self.hasFocus():
            super().wheelEvent(event)
            return None
        event.ignore()
class CollapsibleSection(QWidget):
    '''A collapsible section widget with optional help text.'''
    def __init__(self, title = None, help_text = None, parent = None):
        super().__init__(parent)
        self._is_collapsed = False
        self._title = title
        self._help_text = help_text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        self._header = QPushButton()
        self._header.setProperty('class', 'section-header')
        self._header.setCheckable(True)
        self._header.clicked.connect(self._toggle)
        self._header.setFocusPolicy(Qt.StrongFocus)
        self.set_title(title, help_text)
        layout.addWidget(self._header)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(8)
        layout.addWidget(self._content)
    def set_title(self, title=None, help_text=None):
        '''Update title/help text and refresh header text, tooltip, and accessibility.'''
        self._title = title or ''
        if help_text is not None:
            self._help_text = help_text
        self._refresh_header()

    def _refresh_header(self):
        prefix = '▶' if self._is_collapsed else '▼'
        self._header.setText(f'{prefix} {self._title}')
        if self._help_text:
            self._header.setToolTip(
                f"<b>{self._title}</b><br><span style='color: #a0a0a5;'>{self._help_text}</span>"
            )
        else:
            self._header.setToolTip('')
        self._header.setAccessibleName(f"{self._title} {tr('Section')}")
        if self._is_collapsed:
            desc = f"{tr('Collapsed section for')} {self._title} {tr('settings. Press Enter or Space to expand.')}"
        else:
            desc = f"{tr('Expanded section for')} {self._title} {tr('settings. Press Enter or Space to collapse.')}"
        self._header.setAccessibleDescription(desc)

    def add_widget(self, widget = None):
        '''Add widget to content area.'''
        self._content_layout.addWidget(widget)
    def add_layout(self, layout):
        '''Add layout to content area.'''
        self._content_layout.addLayout(layout)
    def _toggle(self):
        '''Toggle collapsed state.'''
        self._is_collapsed = not (self._is_collapsed)
        if self._is_collapsed:
            self._content.setMaximumHeight(0)
            self._refresh_header()
            return None
        self._content.setMaximumHeight(16777215)
        self._refresh_header()
class ColorButton(QPushButton):
    '''Button that displays and allows selecting a color.'''
    color_changed = Signal(str)
    def __init__(self, color = None, parent = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(32, 32)
        self._update_style()
        self.clicked.connect(self._pick_color)
        self.setFocusPolicy(Qt.StrongFocus)
        self._update_accessibility()
    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value=None):
        self._color = value
        self._update_style()
        self._update_accessibility()
        self.color_changed.emit(value)
    def _update_style(self):
        self.setStyleSheet(f'''\n            QPushButton {{\n                background-color: {self._color};\n                border: 2px solid #3a3a40;\n                border-radius: 4px;\n            }}\n        ''')
    def _update_accessibility(self):
        '''Update accessibility information with current color.'''
        self.setAccessibleName(f"{tr('Color')}: {self._color}")
        self.setAccessibleDescription(f"{tr('Currently selected color is')} {self._color}. {tr('Press Enter or Space to open the color picker dialog.')}")
    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self.window(), tr('Select Color'))
        if color.isValid():
            self.color = color.name()
            return None
class ControlPanel(QWidget):
    '''
    Right-side control panel.
    Contains:
    - Process button
    - Background settings
    - Shadow settings
    - Edge refinement
    - Export settings
    '''
    process_clicked = Signal()
    background_changed = Signal()
    shadow_changed = Signal()
    edge_changed = Signal()
    position_changed = Signal()
    smart_crop_clicked = Signal()
    reset_position_clicked = Signal()
    export_clicked = Signal()
    quick_save_clicked = Signal()
    compare_clicked = Signal()
    auto_enhance_clicked = Signal()
    model_changed = Signal(str)
    language_changed = Signal(str)
    gpu_toggled = Signal(bool)
    gpu_retry_clicked = Signal()
    apply_to_all_clicked = Signal()
    save_all_clicked = Signal()
    save_current_clicked = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self._background_type = 'transparent'
        self._background_color = '#ffffff'
        self._gradient_preset = 'ocean'
        self._background_image = None
        self._shadow_preset = 'soft'
        self._shadow_enabled = True
        self._export_format = 'png'
        self._selected_platforms = []
        self._current_language = get_language()
        self._setup_ui()
        self.retranslate_ui()
        self._connect_signals()
    def _setup_ui(self):
        '''Setup the control panel UI.'''
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setProperty('class', 'control-scroll')
        scroll.setStyleSheet('\n            QScrollArea { border: none; }\n            QScrollBar:vertical {\n                background: transparent;\n                width: 6px;\n                margin: 0;\n            }\n            QScrollBar::handle:vertical {\n                background: #3a3a40;\n                border-radius: 3px;\n                min-height: 20px;\n            }\n            QScrollBar::handle:vertical:hover {\n                background: #4a4a50;\n            }\n            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n                height: 0px;\n            }\n            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n                background: transparent;\n            }\n        ')
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        quick_frame = QFrame()
        quick_frame.setStyleSheet('\n            QFrame {\n                background: rgba(79, 70, 229, 0.05);\n                border: 1px solid rgba(79, 70, 229, 0.2);\n                border-radius: 8px;\n                padding: 8px;\n            }\n        ')
        quick_layout = QVBoxLayout(quick_frame)
        quick_layout.setContentsMargins(8, 8, 8, 8)
        quick_layout.setSpacing(8)
        self.quick_label = QLabel(tr('Quick Settings'))
        self.quick_label.setStyleSheet('font-weight: bold; color: #4F46E5; background: transparent; border: none;')
        quick_layout.addWidget(self.quick_label)
        model_header = QHBoxLayout()
        self.model_label = QLabel(tr('AI Model'))
        self.model_label.setStyleSheet('color: #a0a0a5; font-size: 12px; background: transparent; border: none;')
        model_header.addWidget(self.model_label)
        self.model_help_btn = QPushButton('?')
        self.model_help_btn.setFixedSize(20, 20)
        self.model_help_btn.setToolTip(tr('Click to see model comparison'))
        self.model_help_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 10px;\n                color: #a0a0a5;\n                font-size: 11px;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n                color: #ffffff;\n            }\n        ')
        self.model_help_btn.clicked.connect(self._show_model_comparison)
        model_header.addWidget(self.model_help_btn)
        model_header.addStretch()
        quick_layout.addLayout(model_header)
        self.model_combo = NoWheelComboBox()
        self.model_combo.setFocusPolicy(Qt.StrongFocus)
        self.model_combo.setStyleSheet('\n            QComboBox {\n                background-color: #1a1a1d;\n                border: 1px solid #3a3a40;\n                border-radius: 6px;\n                padding: 6px 10px;\n                color: #ffffff;\n            }\n            QComboBox:hover {\n                border-color: #4F46E5;\n            }\n            QComboBox::drop-down {\n                border: none;\n                padding-right: 8px;\n            }\n            QComboBox QAbstractItemView {\n                background-color: #1a1a1d;\n                border: 1px solid #3a3a40;\n                selection-background-color: #4F46E5;\n                color: #ffffff;\n            }\n        ')
        self._populate_model_combo()
        self.model_combo.setToolTip('')
        quick_layout.addWidget(self.model_combo)
        self.model_desc_label = QLabel()
        self.model_desc_label.setWordWrap(True)
        self.model_desc_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.model_desc_label.setMinimumWidth(0)
        self.model_desc_label.setStyleSheet('color: #606065; font-size: 11px; background: transparent; border: none;')
        self._update_model_description()
        quick_layout.addWidget(self.model_desc_label)
        language_layout = QHBoxLayout()
        self.language_label = QLabel(tr('Language'))
        self.language_label.setStyleSheet('color: #a0a0a5; font-size: 12px; background: transparent; border: none;')
        self.language_combo = NoWheelComboBox()
        self.language_combo.setFocusPolicy(Qt.StrongFocus)
        for lang_key, lang_name in LANGUAGES.items():
            self.language_combo.addItem(lang_name, lang_key)
        lang_idx = self.language_combo.findData(self._current_language)
        if lang_idx >= 0:
            self.language_combo.setCurrentIndex(lang_idx)
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo, 1)
        quick_layout.addLayout(language_layout)
        gpu_layout = QHBoxLayout()
        gpu_layout.setSpacing(8)
        self.gpu_check = QCheckBox(tr('Use GPU acceleration'))
        self.gpu_check.setChecked(True)
        self.gpu_check.setToolTip(tr('Use CUDA acceleration when available; falls back to CPU if GPU inference fails.'))
        gpu_layout.addWidget(self.gpu_check, 1)
        self.gpu_retry_btn = QPushButton(tr('Retry GPU'))
        self.gpu_retry_btn.setFixedHeight(28)
        self.gpu_retry_btn.setToolTip(tr('Retry GPU initialization after a fallback.'))
        self.gpu_retry_btn.setStyleSheet('''
            QPushButton {
                background-color: #2a2a2f;
                border: 1px solid #3a3a40;
                border-radius: 5px;
                color: #a0a0a5;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a3a40;
                color: #ffffff;
                border-color: #4F46E5;
            }
            QPushButton:disabled {
                color: #3a3a40;
                border-color: #2a2a2f;
            }
        ''')
        gpu_layout.addWidget(self.gpu_retry_btn)
        quick_layout.addLayout(gpu_layout)
        self.gpu_status_label = QLabel(tr('GPU status: checking...'))
        self.gpu_status_label.setWordWrap(True)
        self.gpu_status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.gpu_status_label.setMinimumWidth(0)
        self.gpu_status_label.setMaximumWidth(300)
        self.gpu_status_label.setStyleSheet('color: #606065; font-size: 11px; background: transparent; border: none;')
        quick_layout.addWidget(self.gpu_status_label)
        self.auto_process_check = QCheckBox(tr('Auto-process on drop'))
        self.auto_process_check.setToolTip('')
        self.auto_process_check.setChecked(False)
        quick_layout.addWidget(self.auto_process_check)
        layout.addWidget(quick_frame)
        self.process_btn = QPushButton('  ' + tr('Remove Background'))
        self.process_btn.setIcon(get_icon('process', 20))
        self.process_btn.setIconSize(QSize(20, 20))
        self.process_btn.setFixedHeight(52)
        self.process_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.process_btn.setMinimumWidth(0)
        self.process_btn.setToolTip('')
        self.process_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 8px;\n                color: white;\n                font-size: 14px;\n                font-weight: 600;\n                padding: 0 20px;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n            QPushButton:pressed {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #3730A3, stop:1 #5B21B6);\n            }\n            QPushButton:disabled {\n                background: #2a2a2f;\n                color: #606065;\n            }\n        ')
        layout.addWidget(self.process_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(tr('Processing...') + ' %p%')
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status_label.setMinimumWidth(0)
        self.status_label.setMaximumWidth(300)
        self.status_label.setStyleSheet('color: #22c55e; font-weight: bold; padding: 8px;')
        self.status_label.hide()
        layout.addWidget(self.status_label)
        self.quick_actions = QWidget()
        quick_actions_layout = QHBoxLayout(self.quick_actions)
        quick_actions_layout.setContentsMargins(0, 0, 0, 0)
        quick_actions_layout.setSpacing(8)
        self.quick_save_btn = QPushButton(tr('Quick Save PNG'))
        self.quick_save_btn.setIcon(get_icon('save', 16))
        self.quick_save_btn.setIconSize(QSize(16, 16))
        self.quick_save_btn.setFixedHeight(36)
        self.quick_save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.quick_save_btn.setMinimumWidth(0)
        self.quick_save_btn.setToolTip('')
        quick_actions_layout.addWidget(self.quick_save_btn, 1)
        self.compare_btn = QPushButton(tr('Compare'))
        self.compare_btn.setIcon(get_icon('compare', 16))
        self.compare_btn.setIconSize(QSize(16, 16))
        self.compare_btn.setFixedHeight(36)
        self.compare_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.compare_btn.setMinimumWidth(0)
        self.compare_btn.setToolTip('')
        quick_actions_layout.addWidget(self.compare_btn, 1)
        self.quick_actions.hide()
        layout.addWidget(self.quick_actions)
        self.auto_enhance_btn = QPushButton('✨ ' + tr('Auto-Enhance'))
        self.auto_enhance_btn.setFixedHeight(40)
        self.auto_enhance_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.auto_enhance_btn.setMinimumWidth(0)
        self.auto_enhance_btn.setToolTip('')
        self.auto_enhance_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 8px;\n                color: white;\n                font-weight: bold;\n                font-size: 14px;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n            QPushButton:pressed {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #3730A3, stop:1 #5B21B6);\n            }\n            QPushButton:disabled {\n                background: #2a2a2f;\n                color: #606065;\n            }\n        ')
        self.auto_enhance_btn.hide()
        layout.addWidget(self.auto_enhance_btn)
        self.batch_actions_frame = QFrame()
        self.batch_actions_frame.setStyleSheet('\n            QFrame {\n                background: rgba(34, 197, 94, 0.05);\n                border: 1px solid rgba(34, 197, 94, 0.3);\n                border-radius: 8px;\n                padding: 8px;\n            }\n        ')
        batch_actions_layout = QVBoxLayout(self.batch_actions_frame)
        batch_actions_layout.setContentsMargins(8, 8, 8, 8)
        batch_actions_layout.setSpacing(8)
        self.batch_label = QLabel(tr('Batch Actions'))
        self.batch_label.setStyleSheet('font-weight: bold; color: #22c55e; background: transparent; border: none;')
        batch_actions_layout.addWidget(self.batch_label)
        self.apply_to_all_btn = QPushButton(tr('Apply Settings to All'))
        self.apply_to_all_btn.setFixedHeight(36)
        self.apply_to_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.apply_to_all_btn.setMinimumWidth(0)
        self.apply_to_all_btn.setToolTip('')
        self.apply_to_all_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 6px;\n                color: #ffffff;\n                font-weight: 500;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n                border-color: #22c55e;\n            }\n        ')
        batch_actions_layout.addWidget(self.apply_to_all_btn)
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        self.save_current_btn = QPushButton(tr('Save Current'))
        self.save_current_btn.setFixedHeight(36)
        self.save_current_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.save_current_btn.setMinimumWidth(0)
        self.save_current_btn.setToolTip(tr('Save the currently selected image'))
        self.save_current_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 6px;\n                color: #a0a0a5;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n                color: #ffffff;\n            }\n        ')
        save_row.addWidget(self.save_current_btn, 1)
        self.save_all_btn = QPushButton(tr('Save All'))
        self.save_all_btn.setFixedHeight(36)
        self.save_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.save_all_btn.setMinimumWidth(0)
        self.save_all_btn.setToolTip('')
        self.save_all_btn.setStyleSheet('\n            QPushButton {\n                background-color: #22c55e;\n                border: none;\n                border-radius: 6px;\n                color: white;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #16a34a;\n            }\n        ')
        save_row.addWidget(self.save_all_btn, 1)
        batch_actions_layout.addLayout(save_row)
        self.batch_status_label = QLabel('')
        self.batch_status_label.setWordWrap(True)
        self.batch_status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.batch_status_label.setMinimumWidth(0)
        self.batch_status_label.setMaximumWidth(280)
        self.batch_status_label.setStyleSheet('color: #7C3AED; font-size: 11px; font-weight: bold; background: transparent; border: none;')
        self.batch_status_label.setAlignment(Qt.AlignCenter)
        self.batch_status_label.hide()
        batch_actions_layout.addWidget(self.batch_status_label)
        self._batch_status_dots = 0
        self._batch_status_timer = QTimer(self)
        self._batch_status_timer.setInterval(500)
        self._batch_status_timer.timeout.connect(self._animate_batch_status)
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setFixedHeight(10)
        self.batch_progress_bar.setTextVisible(False)
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setStyleSheet('\n            QProgressBar {\n                background-color: #1a1a1f;\n                border: 1px solid #2a2a2f;\n                border-radius: 5px;\n            }\n            QProgressBar::chunk {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border-radius: 4px;\n            }\n        ')
        batch_actions_layout.addWidget(self.batch_progress_bar)
        self.batch_info_label = QLabel('0/0 ' + tr('processed'))
        self.batch_info_label.setWordWrap(True)
        self.batch_info_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.batch_info_label.setMinimumWidth(0)
        self.batch_info_label.setMaximumWidth(280)
        self.batch_info_label.setStyleSheet('color: #a0a0a5; font-size: 11px; background: transparent; border: none;')
        self.batch_info_label.setAlignment(Qt.AlignCenter)
        batch_actions_layout.addWidget(self.batch_info_label)
        self.batch_actions_frame.hide()
        layout.addWidget(self.batch_actions_frame)
        self.bg_section = CollapsibleSection('Background', 'Choose transparent, solid color, gradient, or custom image background')
        self._setup_background_section(self.bg_section)
        layout.addWidget(self.bg_section)
        self.shadow_section = CollapsibleSection('Shadow', 'Add realistic drop shadow to make your subject pop')
        self._setup_shadow_section(self.shadow_section)
        layout.addWidget(self.shadow_section)
        self.edge_section = CollapsibleSection('Edge Refinement', 'Fine-tune edges: sharpen for crisp lines, feather for soft blending')
        self._setup_edge_section(self.edge_section)
        layout.addWidget(self.edge_section)
        self.position_section = CollapsibleSection('Position', 'Scale, move, rotate, and flip your subject')
        self._setup_position_section(self.position_section)
        layout.addWidget(self.position_section)
        self.export_section = CollapsibleSection('Export', 'Save in different formats or export for products, sprites, and social')
        self._setup_export_section(self.export_section)
        layout.addWidget(self.export_section)
        layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setFixedWidth(340)
    def _setup_background_section(self, section = None):
        '''Setup background settings.'''
        type_layout = QHBoxLayout()
        self.bg_type_label = QLabel(tr('Type:'))
        self.bg_type_combo = NoWheelComboBox()
        self.bg_type_combo.setFocusPolicy(Qt.StrongFocus)
        self.bg_type_combo.addItems([
            'Transparent',
            'Solid Color',
            'Gradient',
            'Image'])
        type_layout.addWidget(self.bg_type_label)
        type_layout.addWidget(self.bg_type_combo, 1)
        section.add_layout(type_layout)
        self.solid_color_widget = QWidget()
        solid_layout = QHBoxLayout(self.solid_color_widget)
        solid_layout.setContentsMargins(0, 0, 0, 0)
        self.solid_color_label = QLabel(tr('Color:'))
        self.bg_color_btn = ColorButton('#ffffff')
        solid_layout.addWidget(self.solid_color_label)
        solid_layout.addWidget(self.bg_color_btn)
        solid_layout.addStretch()
        section.add_widget(self.solid_color_widget)
        self.solid_color_widget.hide()
        self.gradient_widget = QWidget()
        gradient_layout = QVBoxLayout(self.gradient_widget)
        gradient_layout.setContentsMargins(0, 0, 0, 0)
        self.gradient_preset_label = QLabel(tr('Preset:'))
        self.gradient_combo = NoWheelComboBox()
        self.gradient_combo.setFocusPolicy(Qt.StrongFocus)
        self._populate_gradient_combo()
        gradient_layout.addWidget(self.gradient_preset_label)
        gradient_layout.addWidget(self.gradient_combo)
        colors_layout = QHBoxLayout()
        self.gradient_color1_btn = ColorButton('#2193b0')
        self.gradient_color2_btn = ColorButton('#6dd5ed')
        self.gradient_color1_label = QLabel(tr('Color 1:'))
        colors_layout.addWidget(self.gradient_color1_label)
        colors_layout.addWidget(self.gradient_color1_btn)
        self.gradient_color2_label = QLabel(tr('Color 2:'))
        colors_layout.addWidget(self.gradient_color2_label)
        colors_layout.addWidget(self.gradient_color2_btn)
        gradient_layout.addLayout(colors_layout)
        section.add_widget(self.gradient_widget)
        self.gradient_widget.hide()
        self.image_bg_widget = QWidget()
        image_layout = QVBoxLayout(self.image_bg_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.load_bg_image_btn = QPushButton('  ' + tr('Load Image...'))
        self.load_bg_image_btn.setIcon(get_icon('image', 18))
        self.load_bg_image_btn.setIconSize(QSize(18, 18))
        self.load_bg_image_btn.setFixedHeight(40)
        self.load_bg_image_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 8px;\n                color: white;\n                font-size: 13px;\n                font-weight: 600;\n                padding: 0 16px;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n            QPushButton:pressed {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #3730A3, stop:1 #5B21B6);\n            }\n        ')
        image_layout.addWidget(self.load_bg_image_btn)
        fit_layout = QHBoxLayout()
        self.fit_label = QLabel(tr('Fit:'))
        self.fit_mode_combo = NoWheelComboBox()
        self.fit_mode_combo.setFocusPolicy(Qt.StrongFocus)
        self.fit_mode_combo.addItems([
            'Cover',
            'Contain',
            'Stretch',
            'Tile'])
        fit_layout.addWidget(self.fit_label)
        fit_layout.addWidget(self.fit_mode_combo)
        image_layout.addLayout(fit_layout)
        blur_layout = QHBoxLayout()
        self.bg_blur_label = QLabel(tr('Blur:'))
        self.bg_blur_slider = NoWheelSlider(Qt.Horizontal)
        self.bg_blur_slider.setFocusPolicy(Qt.StrongFocus)
        self.bg_blur_slider.setRange(0, 30)
        self.bg_blur_value = QLabel('0')
        blur_layout.addWidget(self.bg_blur_label)
        blur_layout.addWidget(self.bg_blur_slider)
        blur_layout.addWidget(self.bg_blur_value)
        image_layout.addLayout(blur_layout)
        section.add_widget(self.image_bg_widget)
        self.image_bg_widget.hide()
    def _setup_shadow_section(self, section = None):
        '''Setup shadow settings.'''
        self.shadow_enabled_check = QCheckBox(tr('Enable Shadow'))
        self.shadow_enabled_check.setChecked(True)
        section.add_widget(self.shadow_enabled_check)
        preset_layout = QHBoxLayout()
        self.shadow_preset_label = QLabel(tr('Preset:'))
        self.shadow_preset_combo = NoWheelComboBox()
        self.shadow_preset_combo.setFocusPolicy(Qt.StrongFocus)
        self._populate_shadow_preset_combo()
        self.shadow_preset_combo.setCurrentIndex(1)
        preset_layout.addWidget(self.shadow_preset_label)
        preset_layout.addWidget(self.shadow_preset_combo, 1)
        section.add_layout(preset_layout)
        (blur_layout, self.shadow_blur_slider, self.shadow_blur_spin) = self._create_slider_with_spinbox('Blur:', 0, 100, 25)
        section.add_layout(blur_layout)
        (opacity_layout, self.shadow_opacity_slider, self.shadow_opacity_spin) = self._create_slider_with_spinbox('Opacity:', 0, 100, 30, '%')
        section.add_layout(opacity_layout)
        (distance_layout, self.shadow_distance_slider, self.shadow_distance_spin) = self._create_slider_with_spinbox('Distance:', 0, 50, 8)
        section.add_layout(distance_layout)
        color_layout = QHBoxLayout()
        self.shadow_color_label = QLabel(tr('Color:'))
        self.shadow_color_btn = ColorButton('#000000')
        color_layout.addWidget(self.shadow_color_label)
        color_layout.addWidget(self.shadow_color_btn)
        color_layout.addStretch()
        section.add_layout(color_layout)
    def _setup_edge_section(self, section = None):
        '''Setup edge refinement settings.'''
        (sharp_layout, self.edge_sharp_slider, self.edge_sharp_spin) = self._create_slider_with_spinbox('Sharpness:', -100, 100, 0)
        section.add_layout(sharp_layout)
        (expand_layout, self.edge_expand_slider, self.edge_expand_spin) = self._create_slider_with_spinbox('Expand:', -10, 10, 0, 'px')
        section.add_layout(expand_layout)
        (feather_layout, self.edge_feather_slider, self.edge_feather_spin) = self._create_slider_with_spinbox('Feather:', 0, 20, 0, 'px')
        section.add_layout(feather_layout)
    def _create_slider_with_spinbox(self, label_text, min_val, max_val, default, suffix='', width=60):
        '''Create a linked slider + spin box pair.
        The slider and spin box stay in sync bidirectionally.
        Returns (layout, slider, spinbox).
        '''
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label._i18n_source_text = label_text
        slider = NoWheelSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        spinbox = NoWheelSpinBox()
        spinbox.setFocusPolicy(Qt.StrongFocus)
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default)
        spinbox.setSuffix(suffix)
        spinbox.setFixedWidth(width)
        spinbox.setButtonSymbols(QSpinBox.NoButtons)
        spinbox.setAlignment(Qt.AlignRight)
        spinbox.setStyleSheet('\n            QSpinBox {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                color: #ffffff;\n                font-size: 12px;\n                padding: 2px 4px;\n            }\n            QSpinBox:focus {\n                border-color: #4F46E5;\n            }\n        ')
        def slider_to_spin(val = None):
            spinbox.blockSignals(True)
            spinbox.setValue(val)
            spinbox.blockSignals(False)
        def spin_to_slider(val = None):
            slider.blockSignals(True)
            slider.setValue(val)
            slider.blockSignals(False)
            slider.valueChanged.emit(val)
        slider.valueChanged.connect(slider_to_spin)
        spinbox.valueChanged.connect(spin_to_slider)
        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(spinbox)
        return (layout, slider, spinbox)
    def _setup_position_section(self, section = None):
        '''Setup position transform settings.'''
        (scale_layout, self.position_scale_slider, self.position_scale_spin) = self._create_slider_with_spinbox('Scale:', 10, 300, 100, '%', 65)
        section.add_layout(scale_layout)
        (x_layout, self.position_x_slider, self.position_x_spin) = self._create_slider_with_spinbox('X:', -500, 500, 0, 'px', 70)
        section.add_layout(x_layout)
        (y_layout, self.position_y_slider, self.position_y_spin) = self._create_slider_with_spinbox('Y:', -500, 500, 0, 'px', 70)
        section.add_layout(y_layout)
        (rotation_layout, self.position_rotation_slider, self.position_rotation_spin) = self._create_slider_with_spinbox('Rotation:', -180, 180, 0, '°', 65)
        section.add_layout(rotation_layout)
        flip_layout = QHBoxLayout()
        self.flip_label = QLabel(tr('Flip:'))
        self.flip_h_btn = QPushButton('H')
        self.flip_h_btn.setCheckable(True)
        self.flip_h_btn.setFixedSize(40, 32)
        self.flip_h_btn.setToolTip(tr('Flip Horizontally'))
        self.flip_h_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                color: #a0a0a5;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n            }\n            QPushButton:checked {\n                background-color: #4F46E5;\n                border-color: #4F46E5;\n                color: white;\n            }\n        ')
        self.flip_v_btn = QPushButton('V')
        self.flip_v_btn.setCheckable(True)
        self.flip_v_btn.setFixedSize(40, 32)
        self.flip_v_btn.setToolTip(tr('Flip Vertically'))
        self.flip_v_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                color: #a0a0a5;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n            }\n            QPushButton:checked {\n                background-color: #4F46E5;\n                border-color: #4F46E5;\n                color: white;\n            }\n        ')
        flip_layout.addWidget(self.flip_label)
        flip_layout.addWidget(self.flip_h_btn)
        flip_layout.addWidget(self.flip_v_btn)
        flip_layout.addStretch()
        section.add_layout(flip_layout)
        actions_layout = QHBoxLayout()
        self.smart_crop_btn = QPushButton(tr('Smart Crop'))
        self.smart_crop_btn.setToolTip('')
        self.smart_crop_btn.setFixedHeight(32)
        self.smart_crop_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 4px;\n                color: white;\n                font-weight: 600;\n                padding: 0 12px;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n        ')
        self.reset_position_btn = QPushButton(tr('Reset'))
        self.reset_position_btn.setToolTip(tr('Reset all position transforms'))
        self.reset_position_btn.setFixedHeight(32)
        self.reset_position_btn.setStyleSheet('\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                color: #a0a0a5;\n                padding: 0 12px;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n                color: white;\n            }\n        ')
        actions_layout.addWidget(self.smart_crop_btn)
        actions_layout.addWidget(self.reset_position_btn)
        section.add_layout(actions_layout)
    def _setup_export_section(self, section = None):
        '''Setup export settings.'''
        format_layout = QHBoxLayout()
        self.format_label = QLabel(tr('Format:'))
        self.export_format_combo = NoWheelComboBox()
        self.export_format_combo.setFocusPolicy(Qt.StrongFocus)
        for key, fmt in EXPORT_FORMATS.items():
            self.export_format_combo.addItem(fmt['name'], key)
        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.export_format_combo, 1)
        section.add_layout(format_layout)
        (quality_layout, self.export_quality_slider, self.export_quality_spin) = self._create_slider_with_spinbox('Quality:', 1, 100, 90, '%')
        section.add_layout(quality_layout)
        self.sizes_label = QLabel(tr('Export Sizes:'))
        section.add_widget(self.sizes_label)
        self._platform_checks = { }
        for cat_key, cat_label in PLATFORM_CATEGORIES.items():
            cat_header = QLabel(cat_label)
            cat_header._i18n_source_text = cat_label
            cat_header.setStyleSheet('font-size: 10px; font-weight: bold; color: #4F46E5; letter-spacing: 1px; margin-top: 4px;')
            section.add_widget(cat_header)
            cat_grid = QGridLayout()
            cat_grid.setSpacing(2)
            (cat_row, cat_col) = (0, 0)
            for key, platform in PLATFORM_SIZES.items():
                if platform.get('category') != cat_key:
                    continue
                check = QCheckBox(platform['name'])
                check.setProperty('platform_key', key)
                self._platform_checks[key] = check
                cat_grid.addWidget(check, cat_row, cat_col)
                cat_col += 1
                if cat_col >= 2:
                    cat_col = 0
                    cat_row += 1
            section.add_layout(cat_grid)
        self.export_btn = QPushButton(tr('Export'))
        self.export_btn.setIcon(get_icon('export', 18))
        self.export_btn.setIconSize(QSize(18, 18))
        self.export_btn.setProperty('class', 'secondary-button')
        self.export_btn.setFixedHeight(40)
        section.add_widget(self.export_btn)
    def _connect_signals(self):
        '''Connect internal signals.'''
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.gpu_check.toggled.connect(self.gpu_toggled.emit)
        self.gpu_retry_btn.clicked.connect(self.gpu_retry_clicked.emit)
        self.process_btn.clicked.connect(self.process_clicked.emit)
        self.quick_save_btn.clicked.connect(self.quick_save_clicked.emit)
        self.compare_btn.clicked.connect(self.compare_clicked.emit)
        self.auto_enhance_btn.clicked.connect(self.auto_enhance_clicked.emit)
        self.apply_to_all_btn.clicked.connect(self.apply_to_all_clicked.emit)
        self.save_all_btn.clicked.connect(self.save_all_clicked.emit)
        self.save_current_btn.clicked.connect(self.save_current_clicked.emit)
        self.bg_type_combo.currentIndexChanged.connect(self._on_bg_type_changed)
        self.bg_color_btn.color_changed.connect(lambda _color=None: self.background_changed.emit())
        self.gradient_combo.currentIndexChanged.connect(self._on_gradient_preset_changed)
        self.gradient_color1_btn.color_changed.connect(lambda _color=None: self.background_changed.emit())
        self.gradient_color2_btn.color_changed.connect(lambda _color=None: self.background_changed.emit())
        self.load_bg_image_btn.clicked.connect(self._load_background_image)
        self.bg_blur_slider.valueChanged.connect(self._on_bg_blur_changed)
        self.shadow_enabled_check.toggled.connect(lambda _checked=None: self.shadow_changed.emit())
        self.shadow_preset_combo.currentIndexChanged.connect(self._on_shadow_preset_changed)
        self.shadow_blur_slider.valueChanged.connect(self._on_shadow_blur_changed)
        self.shadow_opacity_slider.valueChanged.connect(self._on_shadow_opacity_changed)
        self.shadow_distance_slider.valueChanged.connect(self._on_shadow_distance_changed)
        self.shadow_color_btn.color_changed.connect(lambda _color=None: self.shadow_changed.emit())
        self.edge_sharp_slider.valueChanged.connect(self._on_edge_sharp_changed)
        self.edge_expand_slider.valueChanged.connect(self._on_edge_expand_changed)
        self.edge_feather_slider.valueChanged.connect(self._on_edge_feather_changed)
        self.position_scale_slider.valueChanged.connect(self._on_position_scale_changed)
        self.position_x_slider.valueChanged.connect(self._on_position_x_changed)
        self.position_y_slider.valueChanged.connect(self._on_position_y_changed)
        self.position_rotation_slider.valueChanged.connect(self._on_position_rotation_changed)
        self.flip_h_btn.toggled.connect(lambda _checked=None: self.position_changed.emit())
        self.flip_v_btn.toggled.connect(lambda _checked=None: self.position_changed.emit())
        self.smart_crop_btn.clicked.connect(self.smart_crop_clicked.emit)
        self.reset_position_btn.clicked.connect(self.reset_position_clicked.emit)
        self.export_btn.clicked.connect(self.export_clicked.emit)
    def _on_language_changed(self, index=None):
        language = self.language_combo.currentData() or 'en'
        set_language(language)
        self._current_language = language
        self.retranslate_ui()
        self.language_changed.emit(language)

    def _set_combo_items(self, combo, items):
        current = combo.currentData()
        current_index = combo.currentIndex()
        combo.blockSignals(True)
        combo.clear()
        for text, data in items:
            combo.addItem(text, data)
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif 0 <= current_index < combo.count():
            combo.setCurrentIndex(current_index)
        combo.blockSignals(False)

    def _set_section_title(self, section, title, help_text=None):
        if not hasattr(section, '_header'):
            return
        if hasattr(section, 'set_title'):
            section.set_title(title, help_text)
            return
        section._title = title
        prefix = '▶' if getattr(section, '_is_collapsed', False) else '▼'
        section._header.setText(f'{prefix} {title}')

    def _translate_child_labels(self):
        for label in self.findChildren(QLabel):
            source = getattr(label, '_i18n_source_text', None)
            if source:
                label.setText(tr(source))

    def _apply_tooltips(self):
        """Refresh language-dependent hover tooltips."""
        self.model_help_btn.setToolTip(tr('Click to see model comparison'))
        self.model_combo.setToolTip(f"""
            <b>{tr('AI Model Selection')}</b><br>
            <b>BiRefNet:</b> {tr('Best quality (products, complex edges)')}<br>
            <b>BiRefNet Portrait:</b> {tr('Tuned for people cutouts')}<br>
            <b>{tr('Portrait Mode')}:</b> {tr('Alpha matting (soft hair, transparent edges)')}<br>
            <span style='color: #4F46E5;'>{tr('Click ? for details')}</span>
        """)
        self.gpu_check.setToolTip(
            f"<b>{tr('Use GPU acceleration')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Use CUDA acceleration when available; falls back to CPU if GPU inference fails.')}</span>"
        )
        self.gpu_retry_btn.setToolTip(tr('Retry GPU initialization after a fallback.'))
        self.auto_process_check.setToolTip(
            f"<b>{tr('Instant Processing')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Automatically remove background when you drop an image.')}</span><br><br>"
            f"<span style='color: #22c55e;'>{tr('Recommended for single images.')}</span><br>"
            f"<span style='color: #f59e0b;'>{tr('Turn off if you want to select a model first.')}</span>"
        )
        self.process_btn.setToolTip(
            f"<b>{tr('Remove Background')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('AI will automatically detect and remove the background')}</span>"
        )
        self.quick_save_btn.setToolTip(
            f"<b>{tr('Quick Save (Ctrl+S)')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Save as PNG with transparent background.')}</span><br><br>"
            f"<span style='color: #22c55e;'>{tr('Best for:')}</span> {tr('Web, apps, further editing')}<br>"
            f"<span style='color: #a0a0a5;'>{tr('Use Export for more options.')}</span>"
        )
        self.compare_btn.setToolTip(
            f"<b>{tr('Compare View (Space)')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Drag the slider to compare before and after.')}</span><br><br>"
            f"<span style='color: #4F46E5;'>{tr('Tip:')}</span> {tr('Press Space to quickly toggle views.')}"
        )
        self.auto_enhance_btn.setToolTip(
            f"<b>✨ {tr('Auto-Enhance')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('AI analyzes your image and applies:')}</span><br>"
            f"• {tr('Optimal edge refinement')}<br>"
            f"• {tr('Smart defringing')}<br>"
            f"• {tr('Subject centering')}<br>"
            f"<span style='color: #22c55e;'>{tr('One click to perfection!')}</span>"
        )
        self.apply_to_all_btn.setToolTip(
            f"<b>{tr('Apply to All Images')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Copy current background, shadow, and position settings to all images in batch.')}</span>"
        )
        self.save_current_btn.setToolTip(tr('Save the currently selected image'))
        self.save_all_btn.setToolTip(
            f"<b>{tr('Save All Images')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Export all processed images to a folder.')}</span>"
        )
        self.flip_h_btn.setToolTip(tr('Flip Horizontally'))
        self.flip_v_btn.setToolTip(tr('Flip Vertically'))
        self.smart_crop_btn.setToolTip(
            f"<b>{tr('Smart Crop')}</b><br>"
            f"<span style='color: #a0a0a5;'>{tr('Automatically centers and scales your subject to fill the frame.')}</span><br><br>"
            f"<span style='color: #22c55e;'>{tr('Great for:')}</span> {tr('Product photos, profile pictures')}<br>"
            f"<span style='color: #a0a0a5;'>{tr('Click Reset to restore original position.')}</span>"
        )
        self.reset_position_btn.setToolTip(tr('Reset all position transforms'))

    def retranslate_ui(self):
        self.quick_label.setText(tr('Quick Settings'))
        self.model_label.setText(tr('AI Model'))
        self.language_label.setText(tr('Language'))
        self.gpu_check.setText(tr('Use GPU acceleration'))
        self.gpu_retry_btn.setText(tr('Retry GPU'))
        self.auto_process_check.setText(tr('Auto-process on drop'))
        self.process_btn.setText('  ' + tr('Remove Background'))
        self.progress_bar.setFormat(tr('Processing...') + ' %p%')
        self.quick_save_btn.setText(tr('Quick Save PNG'))
        self.compare_btn.setText(tr('Compare'))
        self.auto_enhance_btn.setText('✨ ' + tr('Auto-Enhance'))
        self.batch_label.setText(tr('Batch Actions'))
        self.apply_to_all_btn.setText(tr('Apply Settings to All'))
        self.save_current_btn.setText(tr('Save Current'))
        self.save_all_btn.setText(tr('Save All'))
        self.batch_info_label.setText('0/0 ' + tr('processed'))
        self._set_section_title(self.bg_section, tr('Background'), tr('Choose transparent, solid color, gradient, or custom image background'))
        self._set_section_title(self.shadow_section, tr('Shadow'), tr('Add realistic drop shadow to make your subject pop'))
        self._set_section_title(self.edge_section, tr('Edge Refinement'), tr('Fine-tune edges: sharpen for crisp lines, feather for soft blending'))
        self._set_section_title(self.position_section, tr('Position'), tr('Scale, move, rotate, and flip your subject'))
        self._set_section_title(self.export_section, tr('Export'), tr('Save in different formats or export for products, sprites, and social'))
        self.bg_type_label.setText(tr('Type:'))
        self.solid_color_label.setText(tr('Color:'))
        self.gradient_preset_label.setText(tr('Preset:'))
        self.gradient_color1_label.setText(tr('Color 1:'))
        self.gradient_color2_label.setText(tr('Color 2:'))
        self.fit_label.setText(tr('Fit:'))
        self.bg_blur_label.setText(tr('Blur:'))
        self.shadow_enabled_check.setText(tr('Enable Shadow'))
        self.shadow_preset_label.setText(tr('Preset:'))
        self.shadow_color_label.setText(tr('Color:'))
        self.flip_label.setText(tr('Flip:'))
        self.smart_crop_btn.setText(tr('Smart Crop'))
        self.reset_position_btn.setText(tr('Reset'))
        self.format_label.setText(tr('Format:'))
        self.sizes_label.setText(tr('Export Sizes:'))
        self.export_btn.setText(tr('Export'))
        self.load_bg_image_btn.setText('  ' + tr('Load Image...'))
        self._set_combo_items(self.bg_type_combo, [(tr('Transparent'), 0), (tr('Solid Color'), 1), (tr('Gradient'), 2), (tr('Image'), 3)])
        self._set_combo_items(self.fit_mode_combo, [(tr('Cover'), 'cover'), (tr('Contain'), 'contain'), (tr('Stretch'), 'stretch'), (tr('Tile'), 'tile')])
        self._populate_gradient_combo(refresh=True)
        self._populate_shadow_preset_combo(refresh=True)
        self._translate_child_labels()
        self._populate_model_combo(refresh=True)
        self._update_model_description()
        self._apply_tooltips()

    def _populate_gradient_combo(self, refresh=False):
        current = self.gradient_combo.currentData() if hasattr(self, 'gradient_combo') else None
        self.gradient_combo.blockSignals(True)
        if refresh:
            self.gradient_combo.clear()
        for key, preset in GRADIENT_PRESETS.items():
            if refresh or self.gradient_combo.findData(key) < 0:
                self.gradient_combo.addItem(tr(preset['name']), key)
        idx = self.gradient_combo.findData(current or self._gradient_preset or 'ocean')
        if idx >= 0:
            self.gradient_combo.setCurrentIndex(idx)
        self.gradient_combo.blockSignals(False)

    def _populate_shadow_preset_combo(self, refresh=False):
        current = self.shadow_preset_combo.currentData() if hasattr(self, 'shadow_preset_combo') else None
        self.shadow_preset_combo.blockSignals(True)
        if refresh:
            self.shadow_preset_combo.clear()
        for key, preset in SHADOW_PRESETS.items():
            if refresh or self.shadow_preset_combo.findData(key) < 0:
                self.shadow_preset_combo.addItem(tr(preset['name']), key)
        idx = self.shadow_preset_combo.findData(current or self._shadow_preset or 'soft')
        if idx >= 0:
            self.shadow_preset_combo.setCurrentIndex(idx)
        self.shadow_preset_combo.blockSignals(False)

    def _populate_model_combo(self, refresh=False):
        '''Populate the model combo box with available models.'''
        current = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        if refresh:
            self.model_combo.clear()
        for key in MODEL_DISPLAY_ORDER:
            if key in MODEL_CONFIG:
                config = MODEL_CONFIG[key]
                if refresh or self.model_combo.findData(key) < 0:
                    self.model_combo.addItem(tr_model_display(key, config['display_name']), key)
        target = current or DEFAULT_SETTINGS.get('default_model', 'birefnet')
        idx = self.model_combo.findData(target)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.blockSignals(False)
        return None
    def _update_model_description(self):
        '''Update the model description label based on current selection.'''
        model_key = self.model_combo.currentData()
        if model_key and model_key in MODEL_CONFIG:
            config = MODEL_CONFIG[model_key]
            desc = config.get('description', '')
            size = config.get('size', '')
            self.model_desc_label.setText(f'''{tr_model_description(desc)} ({size})''')
            return None
        self.model_desc_label.setText('')
    def _on_model_changed(self, index = None):
        '''Handle model selection change.'''
        self._update_model_description()
        model_key = self.model_combo.currentData()
        if model_key:
            self.model_changed.emit(model_key)
            logger.info(f'''Model changed to: {model_key}''')
            return None
    def _show_model_comparison(self):
        '''Show a dialog with model comparison information.'''
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Model Comparison'))
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet('\n            QDialog {\n                background-color: #1a1a1d;\n            }\n            QTextBrowser {\n                background-color: #0f0f10;\n                border: 1px solid #2a2a2f;\n                border-radius: 8px;\n                padding: 16px;\n                color: #ffffff;\n            }\n        ')
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        if get_language() == 'zh_CN':
            browser.setHtml('\n                <style>\n                    body { font-family: \'Segoe UI\', sans-serif; color: #ffffff; }\n                    h2 { color: #4F46E5; margin-bottom: 8px; }\n                    h3 { color: #a0a0a5; margin-top: 16px; margin-bottom: 4px; }\n                    .model { margin-bottom: 16px; padding: 12px; background: #2a2a2f; border-radius: 8px; }\n                    .name { font-weight: bold; font-size: 14px; color: #ffffff; }\n                    .quality { color: #22c55e; }\n                    .desc { color: #a0a0a5; font-size: 12px; margin-top: 4px; }\n                    .best { color: #22c55e; font-size: 11px; }\n                </style>\n                <h2>选择合适的模型</h2>\n                <div class="model">\n                    <span class="name quality">BiRefNet（最佳质量）</span>\n                    <span class="best"> - 默认</span>\n                    <div class="desc">最高质量抠图，适合商品、复杂边缘、毛发/透明物体和最终出图。<br>大小：约 928MiB</div>\n                </div>\n                <div class="model">\n                    <span class="name quality">BiRefNet 人像（人物）</span>\n                    <div class="desc">针对人物硬边抠图优化，适合全身照、复杂背景人物和干净轮廓。<br>大小：约 928MiB</div>\n                </div>\n                <div class="model">\n                    <span class="name" style="color: #a78bfa;">人像模式（MODNet）</span>\n                    <div class="desc">Alpha matting，会生成柔和透明边缘，适合发丝、柔边和自然人像。<br>大小：约 25MiB</div>\n                </div>\n                <h3>怎么选？</h3>\n                <p style="color: #a0a0a5; font-size: 12px;">商品/物体/清晰边缘用 BiRefNet；人物硬边用 BiRefNet 人像；发丝和柔边用人像模式。</p>\n            ')
        else:
            browser.setHtml('\n            <style>\n                body { font-family: \'Segoe UI\', sans-serif; color: #ffffff; }\n                h2 { color: #4F46E5; margin-bottom: 8px; }\n                h3 { color: #a0a0a5; margin-top: 16px; margin-bottom: 4px; }\n                .model { margin-bottom: 16px; padding: 12px; background: #2a2a2f; border-radius: 8px; }\n                .name { font-weight: bold; font-size: 14px; color: #ffffff; }\n                .quality { color: #22c55e; }\n                .desc { color: #a0a0a5; font-size: 12px; margin-top: 4px; }\n                .best { color: #22c55e; font-size: 11px; }\n            </style>\n\n            <h2>Choose the Right Model</h2>\n\n            <div class="model">\n                <span class="name quality">BiRefNet (Best Quality)</span>\n                <span class="best"> - DEFAULT</span>\n                <div class="desc">\n                    Highest quality background removal. Handles products,\n                    complex edges, and fine details. Best for:<br>\n                    - E-commerce product photos<br>\n                    - Images with complex edges (hair, fur, transparent objects)<br>\n                    - Final production work<br>\n                    <br>Size: ~928MiB\n                </div>\n            </div>\n\n            <div class="model">\n                <span class="name quality">BiRefNet Portrait (People)</span>\n                <div class="desc">\n                    Same BiRefNet quality, tuned for human subjects. Produces\n                    the best hard-edge cutouts of people. Best for:<br>\n                    - Full body photos and silhouettes<br>\n                    - People on busy backgrounds<br>\n                    - Clean product-style people cutouts<br>\n                    <br>Size: ~928MiB\n                </div>\n            </div>\n\n            <div class="model">\n                <span class="name" style="color: #a78bfa;">Portrait Mode (MODNet)</span>\n                <div class="desc">\n                    Alpha matting — produces smooth gradients of transparency\n                    instead of hard edges. Individual hair strands get partial\n                    opacity. Nothing else does this. Best for:<br>\n                    - Wispy hair and soft edges<br>\n                    - Natural-looking portraits<br>\n                    - Semi-transparent transitions<br>\n                    <br>Size: ~25MiB\n                </div>\n            </div>\n\n            <h3>When to use which?</h3>\n            <p style="color: #a0a0a5; font-size: 12px;">\n                <b style="color: #22c55e;">Products, objects, crisp edges?</b>\n                Use BiRefNet — it\'s the default for a reason.<br>\n                <b style="color: #22c55e;">People with clean cutout?</b>\n                Use BiRefNet Portrait.<br>\n                <b style="color: #a78bfa;">Soft hair, transparent edges?</b>\n                Use Portrait Mode — it\'s the only one that does alpha matting.\n            </p>\n        ')
        layout.addWidget(browser)
        close_btn = QPushButton(tr('Got it!'))
        close_btn.setStyleSheet('\n            QPushButton {\n                background-color: #4F46E5;\n                border: none;\n                border-radius: 6px;\n                padding: 10px 24px;\n                color: white;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: #4338CA;\n            }\n        ')
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()
    def get_selected_model(self):
        '''Get the currently selected model key.'''
        return self.model_combo.currentData() or DEFAULT_SETTINGS.get('default_model', 'birefnet')
    def set_selected_model(self, model_key = None):
        '''Set the selected model by key.'''
        idx = self.model_combo.findData(model_key)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
            return None
    def _on_bg_type_changed(self, index = None):
        '''Handle background type change.'''
        self.solid_color_widget.hide()
        self.gradient_widget.hide()
        self.image_bg_widget.hide()
        if index == 0:
            self._background_type = 'transparent'
        elif index == 1:
            self._background_type = 'solid'
            self.solid_color_widget.show()
        elif index == 2:
            self._background_type = 'gradient'
            self.gradient_widget.show()
        elif index == 3:
            self._background_type = 'image'
            self.image_bg_widget.show()
        self.background_changed.emit()
    def _on_gradient_preset_changed(self, index = None):
        '''Handle gradient preset change.'''
        key = self.gradient_combo.currentData()
        if not key:
            return None
        preset = GRADIENT_PRESETS.get(key)
        if not preset:
            logger.warning(f'''Unknown gradient preset: {key}''')
            return None
        self.gradient_color1_btn.blockSignals(True)
        self.gradient_color2_btn.blockSignals(True)
        try:
            self.gradient_color1_btn.color = preset.get('color1', '#2193b0')
            self.gradient_color2_btn.color = preset.get('color2', '#6dd5ed')
        finally:
            self.gradient_color1_btn.blockSignals(False)
            self.gradient_color2_btn.blockSignals(False)
        self.background_changed.emit()
        return None
    def _load_background_image(self):
        '''Load background image.'''
        (file_path, _) = QFileDialog.getOpenFileName(self, tr('Select Background Image'), '', tr('Images (*.png *.jpg *.jpeg *.webp)'))
        if not file_path:
            return None
        with Image.open(file_path) as img:
            img.load()
            self._background_image = img.copy()
        self.background_changed.emit()
        logger.info(f'''Loaded background image: {file_path}''')
        return None

    def _on_bg_blur_changed(self, value = None):
        '''Handle background blur change.'''
        self.bg_blur_value.setText(str(value))
        self.background_changed.emit()
    def _on_shadow_preset_changed(self, index = None):
        '''Handle shadow preset change.'''
        key = self.shadow_preset_combo.currentData()
        if not key:
            return None
        preset = SHADOW_PRESETS.get(key)
        if not preset:
            logger.warning(f'''Unknown shadow preset: {key}''')
            return None
        self.shadow_blur_slider.blockSignals(True)
        self.shadow_opacity_slider.blockSignals(True)
        self.shadow_distance_slider.blockSignals(True)
        self.shadow_color_btn.blockSignals(True)
        try:
            self.shadow_blur_slider.setValue(preset.get('blur', 0))
            self.shadow_opacity_slider.setValue(preset.get('opacity', 50))
            self.shadow_distance_slider.setValue(preset.get('distance', 0))
            self.shadow_color_btn.color = preset.get('color', '#000000')
        finally:
            self.shadow_blur_slider.blockSignals(False)
            self.shadow_opacity_slider.blockSignals(False)
            self.shadow_distance_slider.blockSignals(False)
            self.shadow_color_btn.blockSignals(False)
        self.shadow_opacity_slider.blockSignals(False)
        self.shadow_distance_slider.blockSignals(False)
        self.shadow_color_btn.blockSignals(False)
        self.shadow_changed.emit()
        return None
    def _on_shadow_blur_changed(self, value = None):
        '''Handle shadow blur change.'''
        self.shadow_changed.emit()
    def _on_shadow_opacity_changed(self, value = None):
        '''Handle shadow opacity change.'''
        self.shadow_changed.emit()
    def _on_shadow_distance_changed(self, value = None):
        '''Handle shadow distance change.'''
        self.shadow_changed.emit()
    def _on_edge_sharp_changed(self, value = None):
        '''Handle edge sharpness change.'''
        self.edge_changed.emit()
    def _on_edge_expand_changed(self, value = None):
        '''Handle edge expand change.'''
        self.edge_changed.emit()
    def _on_edge_feather_changed(self, value = None):
        '''Handle edge feather change.'''
        self.edge_changed.emit()
    def _on_position_scale_changed(self, value = None):
        '''Handle position scale change.'''
        self.position_changed.emit()
    def _on_position_x_changed(self, value = None):
        '''Handle position X change.'''
        self.position_changed.emit()
    def _on_position_y_changed(self, value = None):
        '''Handle position Y change.'''
        self.position_changed.emit()
    def _on_position_rotation_changed(self, value = None):
        '''Handle position rotation change.'''
        self.position_changed.emit()
    def get_background_settings(self):
        '''Get current background settings.'''
        settings = { }
        if self._background_type == 'solid':
            settings['color'] = self.bg_color_btn.color
        elif self._background_type == 'gradient':
            settings['color1'] = self.gradient_color1_btn.color
            settings['color2'] = self.gradient_color2_btn.color
            settings['direction'] = 135
        elif self._background_type == 'image':
            if self._background_image is None:
                logger.warning('Image background selected but no image loaded, falling back to transparent')
                return ('transparent', { })
            settings['image'] = self._background_image
            settings['fit_mode'] = self.fit_mode_combo.currentData() or self.fit_mode_combo.currentText().lower()
            settings['blur'] = self.bg_blur_slider.value()
        return (self._background_type, settings)
    def get_shadow_settings(self):
        '''Get current shadow settings.'''
        return ShadowSettings(self.shadow_enabled_check.isChecked(), self.shadow_blur_slider.value(), self.shadow_opacity_slider.value(), self.shadow_distance_slider.value(), 135, self.shadow_color_btn.color)
    def get_edge_settings(self):
        '''Get edge refinement settings.'''
        return {
            'sharpen': self.edge_sharp_slider.value() / 100,
            'expand': self.edge_expand_slider.value(),
            'feather': self.edge_feather_slider.value() }
    def get_export_settings(self):
        '''Get export settings.'''
        export_format = self.export_format_combo.currentData()
        if not export_format:
            export_format = 'png'
        return ExportSettings(format=export_format.upper(), quality=self.export_quality_slider.value())
    def get_selected_platforms(self):
        '''Get selected platform keys.'''
        return [key for key, check in self._platform_checks.items() if check.isChecked()]
    def get_position_settings(self):
        '''Get current position transform settings.'''
        return {
            'scale': self.position_scale_slider.value() / 100,
            'x': self.position_x_slider.value(),
            'y': self.position_y_slider.value(),
            'rotation': self.position_rotation_slider.value(),
            'flip_h': self.flip_h_btn.isChecked(),
            'flip_v': self.flip_v_btn.isChecked() }
    def set_position_values(self, scale: float, x: int = 0, y: int = 0, rotation: int = 0, flip_h: bool = False, flip_v: bool = False):
        '''
        Set position transform values programmatically.
        This is used by smart crop and reset to update the UI without
        triggering recursive signal emissions.
        '''
        widgets = [
            self.position_scale_slider,
            self.position_scale_spin,
            self.position_x_slider,
            self.position_x_spin,
            self.position_y_slider,
            self.position_y_spin,
            self.position_rotation_slider,
            self.position_rotation_spin,
            self.flip_h_btn,
            self.flip_v_btn]
        for w in widgets:
            w.blockSignals(True)
        try:
            scale_int = int(scale * 100)
            self.position_scale_slider.setValue(scale_int)
            self.position_scale_spin.setValue(scale_int)
            self.position_x_slider.setValue(x)
            self.position_x_spin.setValue(x)
            self.position_y_slider.setValue(y)
            self.position_y_spin.setValue(y)
            self.position_rotation_slider.setValue(rotation)
            self.position_rotation_spin.setValue(rotation)
            self.flip_h_btn.setChecked(flip_h)
            self.flip_v_btn.setChecked(flip_v)
        finally:
            for w in widgets:
                w.blockSignals(False)
        return None

    def set_gpu_controls(self, requested: bool = True, available: bool = False, active: bool = False, failed: bool = False, status_text: str = '', detail_text: str = ''):
        """Update GPU checkbox/status without re-emitting user actions."""
        self.gpu_check.blockSignals(True)
        try:
            self.gpu_check.setChecked(bool(requested))
            self.gpu_check.setEnabled(bool(available))
        finally:
            self.gpu_check.blockSignals(False)
        self.gpu_retry_btn.setEnabled(bool(available))
        if failed:
            color = '#f59e0b'
        elif active:
            color = '#22c55e'
        else:
            color = '#a0a0a5'
        label = tr(status_text) if status_text else ''
        if failed and available:
            retry_hint = tr('Click Retry GPU to try acceleration again.')
            label = f"{label}. {retry_hint}" if label else retry_hint
        if detail_text:
            label = f"{label}: {detail_text}" if label else detail_text
        self.gpu_status_label.setText(self._compact_message(label, 96))
        self.gpu_status_label.setToolTip(label)
        self.gpu_status_label.setStyleSheet(f'color: {color}; {GPU_STATUS_BASE}')

    def _compact_message(self, message, max_len=88):
        """Return a single safe status string that cannot widen the panel."""
        text = str(message or '')
        if len(text) <= max_len:
            return text
        head = max(16, int(max_len * 0.56))
        tail = max(12, max_len - head - 1)
        return f'{text[:head]}…{text[-tail:]}'

    def _set_status_message(self, message, style, *, prefix=''):
        """Set status text with middle ellipsis and full text in tooltip."""
        full_text = f'{prefix}{message or ""}'
        compact = self._compact_message(full_text)
        self.status_label.setText(compact)
        self.status_label.setToolTip(full_text)
        self.status_label.setStyleSheet(style)
        self.status_label.show()

    def show_processing(self):
        '''Show processing state with progress bar.'''
        self.process_btn.setEnabled(False)
        self.process_btn.setText('  ' + tr('Processing...'))
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.hide()
        self.quick_actions.hide()
    def update_progress(self, value = None):
        '''Update progress bar (0.0 to 1.0).'''
        self.progress_bar.setValue(int(value * 100))
    def show_success(self, message = None):
        '''Show success state with quick actions.'''
        self.process_btn.setEnabled(True)
        self.process_btn.setText('  ' + tr('Remove Background'))
        self.progress_bar.hide()
        self._set_status_message(
            message,
            STATUS_SUCCESS
        )
        self.quick_actions.show()
        self.auto_enhance_btn.show()
        self.auto_enhance_btn.setEnabled(True)
        QTimer.singleShot(5000, self._hide_success_message)
    def _hide_success_message(self):
        '''Hide the success message but keep quick actions.'''
        self.status_label.hide()
    def show_error(self, message = None):
        '''Show error state.'''
        self.process_btn.setEnabled(True)
        self.process_btn.setText('  ' + tr('Remove Background'))
        self.progress_bar.hide()
        self._set_status_message(
            message,
            STATUS_ERROR,
            prefix='✗ '
        )
        self.quick_actions.hide()
        QTimer.singleShot(5000, self.status_label.hide)
    def reset_state(self):
        '''Reset to initial state.'''
        self.process_btn.setEnabled(True)
        self.process_btn.setText('  ' + tr('Remove Background'))
        self.progress_bar.hide()
        self.status_label.hide()
        self.quick_actions.hide()
        self.auto_enhance_btn.hide()

    def set_status(self, message):
        '''Show a neutral status message.'''
        self._set_status_message(
            message,
            STATUS_NEUTRAL
        )
    def is_auto_process_enabled(self):
        '''Check if auto-process on drop is enabled.'''
        return self.auto_process_check.isChecked()
    def show_batch_mode(self):
        '''Enable batch mode UI.'''
        self.batch_actions_frame.show()
        self.quick_save_btn.hide()
    def hide_batch_mode(self):
        '''Disable batch mode UI.'''
        self.batch_actions_frame.hide()
        self.quick_save_btn.show()
    def update_batch_info(self, processed: int = 0, total: int = 0, edited: int = 0, saved: int = 0):
        '''Update the batch progress info label and progress bar.'''
        parts = [
            f'''{processed}/{total} {tr('processed')}''']
        if edited > 0:
            parts.append(f'''{edited} {tr('edited')}''')
        if saved > 0:
            parts.append(f'''{saved} {tr('saved')}''')
        self.batch_info_label.setText(' • '.join(parts))
        if processed > 0 and self.batch_progress_bar.maximum() == 0:
            self.batch_progress_bar.setRange(0, 100)
        if total > 0 and self.batch_progress_bar.maximum() > 0:
            pct = int((processed / total) * 100)
            self.batch_progress_bar.setValue(pct)
        if self._batch_status_timer.isActive() or processed < total:
            self.batch_status_label.setText(f'''⚡ {tr('Processing')} {processed}/{total}''')
            return None
    def set_batch_save_enabled(self, enabled = None):
        '''Enable or disable save buttons based on processing state.'''
        self.save_all_btn.setEnabled(enabled)
        self.save_current_btn.setEnabled(enabled)
    def set_batch_processing_active(self, active = None, total = None):
        '''Show or hide the animated processing indicator.'''
        if active:
            self._batch_status_dots = 0
            self.batch_status_label.setText(f'''⚡ {tr('Processing')} {total} {tr('images')}...''')
            self.batch_status_label.show()
            self._batch_status_timer.start()
            self.batch_progress_bar.setRange(0, 0)
            return None
        self._batch_status_timer.stop()
        self.batch_status_label.setText('')
        self.batch_status_label.hide()
        self.batch_progress_bar.setRange(0, 100)
    def _animate_batch_status(self):
        '''Animate the processing status dots.'''
        self._batch_status_dots = (self._batch_status_dots + 1) % 4
        dots = '.' * self._batch_status_dots
        base = self.batch_status_label.text().rstrip('.')
        self.batch_status_label.setText(base + dots)
