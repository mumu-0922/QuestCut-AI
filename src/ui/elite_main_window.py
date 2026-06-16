'''
Elite Main Window
================
Main application window matching ELITE web version layout.
Uses stacked widget to switch between welcome and editor screens.
'''
import logging
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QMessageBox, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, QSettings, QSignalBlocker
from PySide6.QtGui import QKeySequence, QShortcut
from .welcome_screen import WelcomeScreen
from .editor_screen import EditorScreen
from ..core.background_remover import BackgroundRemover
from ..utils.constants import MODEL_CONFIG
from ..utils.i18n import set_language, tr, tr_model_display
from .loading_overlay import LoadingOverlay
from .shortcuts_dialog import ShortcutsDialog
from ..core.portrait_mode import PortraitMode
from ..processing.mask_ops import MaskOperations, BrushStroke, BrushMode
from ..app.history_manager import HistoryManager, HistoryState
from ..controllers.export_controller import ExportController
from ..controllers.batch_controller import BatchController
logger = logging.getLogger(__name__)

APP_NAME = 'QuestCut-AI'
class EliteMainWindow(QMainWindow):
    '''Main application window with ELITE layout.'''
    def __init__(self, parent = None):
        super().__init__(parent)
        self._background_remover = BackgroundRemover()
        self._portrait_mode = PortraitMode()
        self._mask_ops = MaskOperations()
        self._original_image = None
        self._original_rgb_np = None
        self._processed_image = None
        self._current_mask = None
        self._base_mask = None
        self._pre_edge_mask = None
        self._edge_undo_saved = False
        self._current_files = []
        self._is_processing = False
        self._recomposite_timer = QTimer(self)
        self._recomposite_timer.setSingleShot(True)
        self._recomposite_timer.setInterval(16)
        self._recomposite_timer.timeout.connect(self._recomposite_with_mask)
        self._position_scale = 1
        self._position_x = 0
        self._position_y = 0
        self._rotation = 0
        self._flip_h = False
        self._flip_v = False
        self._active_tool = 'none'
        self._batch_mode = False
        self._batch_queue = None
        self._batch_save_manager = None
        self._batch_output_dir = None
        self._batch_config = None
        self._batch_start_time = None
        self._batch_images = []
        self._batch_current_index = 0
        self._batch_global_settings = { }
        self._batch_processing_complete = False
        self._export_manager = None
        self._batch_export_progress = None
        self._setup_ui()
        self._export_controller = ExportController(self)
        self._batch_controller = BatchController(self)
        self._history = HistoryManager(
            capture_state=self._capture_history_state,
            restore_state=self._restore_history_state,
            has_state=self._has_history_state,
            sync_after_mutation=self._sync_current_batch_state,
            clear_aux_history=self._mask_ops.clear_history,
            changed_callback=self._update_undo_redo_state,
            max_history=30,
        )
        self._connect_signals()
        self._setup_shortcuts()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1220, 800)
        self.resize(1400, 900)
        QTimer.singleShot(500, self._check_first_run)
    def _setup_ui(self):
        '''Setup the main UI with stacked screens.'''
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.welcome_screen = WelcomeScreen()
        self.stack.addWidget(self.welcome_screen)
        self.editor_screen = EditorScreen()
        self.stack.addWidget(self.editor_screen)
        self._loading_overlay = LoadingOverlay(self.editor_screen)
        self.stack.setCurrentIndex(0)
        self.setStyleSheet("\n            QMainWindow {\n                background-color: #0f0f10;\n            }\n            QWidget {\n                background-color: transparent;\n                color: #ffffff;\n                font-family: 'Segoe UI', -apple-system, sans-serif;\n            }\n            QLabel {\n                color: #a0a0a5;\n            }\n            QSlider::groove:horizontal {\n                background: #2a2a2f;\n                height: 6px;\n                border-radius: 3px;\n            }\n            QSlider::handle:horizontal {\n                background: #4F46E5;\n                width: 16px;\n                height: 16px;\n                margin: -5px 0;\n                border-radius: 8px;\n            }\n            QSlider::sub-page:horizontal {\n                background: #4F46E5;\n                border-radius: 3px;\n            }\n            QCheckBox::indicator {\n                width: 20px;\n                height: 20px;\n                border: 2px solid #3a3a40;\n                border-radius: 4px;\n                background: #1a1a1d;\n            }\n            QCheckBox::indicator:checked {\n                background: #4F46E5;\n                border-color: #4F46E5;\n            }\n        ")
    def _connect_signals(self):
        '''Connect all signals.'''
        self.welcome_screen.files_selected.connect(self._on_files_selected)
        self.editor_screen.back_requested.connect(self._show_welcome)
        self.editor_screen.toolbar.undo_clicked.connect(self._undo)
        self.editor_screen.toolbar.redo_clicked.connect(self._redo)
        self.editor_screen.toolbar.auto_enhance_clicked.connect(self._auto_enhance)
        self.editor_screen.toolbar.view_toggled.connect(self._on_view_toggled)
        self.editor_screen.toolbar.compare_toggled.connect(self._on_compare_toggled)
        self.editor_screen.toolbar.shortcuts_clicked.connect(self._show_shortcuts)
        self.editor_screen.tool_changed.connect(self._on_tool_changed)
        self.editor_screen.brush_size_changed.connect(self._on_brush_size_changed)
        cp = self.editor_screen.control_panel
        cp.process_clicked.connect(self._process_image)
        cp.export_clicked.connect(self._export_image)
        cp.quick_save_clicked.connect(self._quick_save)
        cp.compare_clicked.connect(lambda: self.editor_screen.canvas.enable_comparison_slider())
        cp.auto_enhance_clicked.connect(self._auto_enhance)
        cp.background_changed.connect(self._on_background_changed)
        cp.shadow_changed.connect(self._on_shadow_changed)
        cp.edge_changed.connect(self._on_edge_changed)
        cp.position_changed.connect(self._on_position_changed)
        cp.smart_crop_clicked.connect(self._on_smart_crop)
        cp.reset_position_clicked.connect(self._on_reset_position)
        cp.model_changed.connect(self._on_model_changed)
        cp.language_changed.connect(self._on_language_changed)
        self.editor_screen.canvas.brush_stroke.connect(self._on_brush_stroke)
        self.editor_screen.canvas.file_dropped.connect(self._on_file_dropped)
        self.editor_screen.canvas.files_dropped.connect(self._on_files_dropped)
        self.editor_screen.filmstrip.image_selected.connect(self._on_batch_image_selected)
        self.editor_screen.filmstrip.thumbnails_loading.connect(self._on_thumbnails_loading)
        self.editor_screen.filmstrip.thumbnails_loaded.connect(self._on_thumbnails_loaded)
        self.editor_screen.filmstrip.add_images_clicked.connect(self._add_batch_images)
        self._background_remover.processing_started.connect(self._on_processing_started)
        self._background_remover.processing_progress.connect(self._on_processing_progress)
        self._background_remover.processing_finished.connect(self._on_ai_finished)
        self._background_remover.processing_error.connect(self._on_processing_error)
        self._portrait_mode.processing_started.connect(self._on_processing_started)
        self._portrait_mode.processing_progress.connect(self._on_processing_progress)
        self._portrait_mode.processing_finished.connect(self._on_portrait_finished)
        self._portrait_mode.processing_error.connect(self._on_processing_error)
        from ..core.model_manager import get_model_manager
        model_manager = get_model_manager()
        model_manager.model_error.connect(self._on_model_error)
        model_manager.gpu_status_changed.connect(self._update_gpu_status)
        model_manager.gpu_runtime_state_changed.connect(self._update_gpu_status)
        cp.gpu_toggled.connect(self._on_gpu_toggled)
        cp.gpu_retry_clicked.connect(self._retry_gpu)
        cp.apply_to_all_clicked.connect(self._apply_current_settings_to_all)
        cp.save_current_clicked.connect(self._save_current_batch_image)
        cp.save_all_clicked.connect(self._save_all_batch_images)
        settings = QSettings('QuestCut', 'QuestCut-AI')
        model_manager.use_gpu = settings.value('use_gpu', True, type=bool)
        saved_language = settings.value('language', self.editor_screen.control_panel.language_combo.currentData() or 'en')
        idx = self.editor_screen.control_panel.language_combo.findData(saved_language)
        if idx >= 0:
            self.editor_screen.control_panel.language_combo.setCurrentIndex(idx)
        self._on_language_changed(saved_language)
        self._update_gpu_status()
        self._update_undo_redo_state()

    def _update_undo_redo_state(self):
        """Enable or disable undo/redo buttons from the real history stacks."""
        toolbar = getattr(self.editor_screen, 'toolbar', None)
        if toolbar is None:
            return None
        history = getattr(self, '_history', None)
        toolbar.set_undo_enabled(bool(history and history.can_undo))
        toolbar.set_redo_enabled(bool(history and history.can_redo))
        return None

    def _clone_mask(self, mask=None):
        return HistoryManager.clone_mask(mask)

    def _clone_image(self, image=None):
        return HistoryManager.clone_image(image)

    def _capture_control_settings(self):
        """Capture edit controls needed to restore visual state."""
        cp = self.editor_screen.control_panel
        return {
            'background_type_index': cp.bg_type_combo.currentIndex(),
            'background_color': cp.bg_color_btn.color,
            'gradient_index': cp.gradient_combo.currentIndex(),
            'gradient_color1': cp.gradient_color1_btn.color,
            'gradient_color2': cp.gradient_color2_btn.color,
            'fit_mode_index': cp.fit_mode_combo.currentIndex(),
            'bg_blur': cp.bg_blur_slider.value(),
            'shadow_enabled': cp.shadow_enabled_check.isChecked(),
            'shadow_preset_index': cp.shadow_preset_combo.currentIndex(),
            'shadow_color': cp.shadow_color_btn.color,
            'shadow_blur': cp.shadow_blur_slider.value(),
            'shadow_opacity': cp.shadow_opacity_slider.value(),
            'shadow_distance': cp.shadow_distance_slider.value(),
            'edge_sharp': cp.edge_sharp_slider.value(),
            'edge_expand': cp.edge_expand_slider.value(),
            'edge_feather': cp.edge_feather_slider.value(),
            'position_scale': cp.position_scale_slider.value(),
            'position_x': cp.position_x_slider.value(),
            'position_y': cp.position_y_slider.value(),
            'position_rotation': cp.position_rotation_slider.value(),
            'flip_h': cp.flip_h_btn.isChecked(),
            'flip_v': cp.flip_v_btn.isChecked(),
        }

    def _capture_history_state(self):
        return HistoryState(
            mask=self._clone_mask(self._current_mask),
            processed_image=self._clone_image(self._processed_image),
            control_settings=self._capture_control_settings(),
        )

    def _clone_history_state(self, state=None):
        return HistoryManager.clone_state(state)

    def _has_history_state(self):
        return self._original_image is not None or self._current_mask is not None or self._processed_image is not None

    def _restore_control_settings(self, settings=None):
        """Restore controls without emitting change signals."""
        if not settings:
            return None
        cp = self.editor_screen.control_panel
        widgets = [
            cp.bg_type_combo,
            cp.bg_color_btn,
            cp.gradient_combo,
            cp.gradient_color1_btn,
            cp.gradient_color2_btn,
            cp.fit_mode_combo,
            cp.bg_blur_slider,
            cp.shadow_enabled_check,
            cp.shadow_preset_combo,
            cp.shadow_color_btn,
            cp.shadow_blur_slider,
            cp.shadow_opacity_slider,
            cp.shadow_distance_slider,
            cp.edge_sharp_slider,
            cp.edge_expand_slider,
            cp.edge_feather_slider,
            cp.position_scale_slider,
            cp.position_scale_spin,
            cp.position_x_slider,
            cp.position_x_spin,
            cp.position_y_slider,
            cp.position_y_spin,
            cp.position_rotation_slider,
            cp.position_rotation_spin,
            cp.flip_h_btn,
            cp.flip_v_btn,
        ]
        blockers = [QSignalBlocker(widget) for widget in widgets]
        try:
            cp.bg_type_combo.setCurrentIndex(settings.get('background_type_index', cp.bg_type_combo.currentIndex()))
            cp.bg_color_btn.color = settings.get('background_color', cp.bg_color_btn.color)
            cp.gradient_combo.setCurrentIndex(settings.get('gradient_index', cp.gradient_combo.currentIndex()))
            cp.gradient_color1_btn.color = settings.get('gradient_color1', cp.gradient_color1_btn.color)
            cp.gradient_color2_btn.color = settings.get('gradient_color2', cp.gradient_color2_btn.color)
            cp.fit_mode_combo.setCurrentIndex(settings.get('fit_mode_index', cp.fit_mode_combo.currentIndex()))
            cp.bg_blur_slider.setValue(settings.get('bg_blur', cp.bg_blur_slider.value()))
            cp.bg_blur_value.setText(str(cp.bg_blur_slider.value()))
            cp.shadow_enabled_check.setChecked(settings.get('shadow_enabled', cp.shadow_enabled_check.isChecked()))
            cp.shadow_preset_combo.setCurrentIndex(settings.get('shadow_preset_index', cp.shadow_preset_combo.currentIndex()))
            cp.shadow_color_btn.color = settings.get('shadow_color', cp.shadow_color_btn.color)
            cp.shadow_blur_slider.setValue(settings.get('shadow_blur', cp.shadow_blur_slider.value()))
            cp.shadow_blur_spin.setValue(cp.shadow_blur_slider.value())
            cp.shadow_opacity_slider.setValue(settings.get('shadow_opacity', cp.shadow_opacity_slider.value()))
            cp.shadow_opacity_spin.setValue(cp.shadow_opacity_slider.value())
            cp.shadow_distance_slider.setValue(settings.get('shadow_distance', cp.shadow_distance_slider.value()))
            cp.shadow_distance_spin.setValue(cp.shadow_distance_slider.value())
            cp.edge_sharp_slider.setValue(settings.get('edge_sharp', cp.edge_sharp_slider.value()))
            cp.edge_sharp_spin.setValue(cp.edge_sharp_slider.value())
            cp.edge_expand_slider.setValue(settings.get('edge_expand', cp.edge_expand_slider.value()))
            cp.edge_expand_spin.setValue(cp.edge_expand_slider.value())
            cp.edge_feather_slider.setValue(settings.get('edge_feather', cp.edge_feather_slider.value()))
            cp.edge_feather_spin.setValue(cp.edge_feather_slider.value())
            cp.position_scale_slider.setValue(settings.get('position_scale', cp.position_scale_slider.value()))
            cp.position_scale_spin.setValue(cp.position_scale_slider.value())
            cp.position_x_slider.setValue(settings.get('position_x', cp.position_x_slider.value()))
            cp.position_x_spin.setValue(cp.position_x_slider.value())
            cp.position_y_slider.setValue(settings.get('position_y', cp.position_y_slider.value()))
            cp.position_y_spin.setValue(cp.position_y_slider.value())
            cp.position_rotation_slider.setValue(settings.get('position_rotation', cp.position_rotation_slider.value()))
            cp.position_rotation_spin.setValue(cp.position_rotation_slider.value())
            cp.flip_h_btn.setChecked(settings.get('flip_h', cp.flip_h_btn.isChecked()))
            cp.flip_v_btn.setChecked(settings.get('flip_v', cp.flip_v_btn.isChecked()))
            cp._on_bg_type_changed(cp.bg_type_combo.currentIndex())
        finally:
            del blockers
        return None

    def _restore_history_state(self, state=None):
        if state is None:
            return None
        self._restore_control_settings(state.control_settings)
        self._current_mask = self._clone_mask(state.mask)
        if self._current_mask is not None:
            self._base_mask = self._current_mask.copy()
            self._pre_edge_mask = self._current_mask.copy()
        else:
            self._base_mask = None
            self._pre_edge_mask = None
        self._processed_image = self._clone_image(state.processed_image)
        if self._processed_image is not None:
            self.editor_screen.canvas.update_result_silent(self._processed_image)
        elif self._current_mask is not None:
            self._recomposite_with_mask()
        else:
            self.editor_screen.canvas.update_result_silent(None)
        self._sync_current_batch_state()
        return None

    def _reset_history(self):
        self._history.reset()

    def _mark_history_baseline(self):
        self._history.mark_baseline()

    def _push_history(self):
        """Save current edit state before a user-visible mutation."""
        return self._history.push()

    def _finish_history_mutation(self):
        """Record the post-mutation baseline and refresh edit controls."""
        return self._history.finish_mutation()

    def _cancel_history_mutation(self):
        """Drop a pending history point when the attempted mutation failed."""
        return self._history.cancel_mutation()

    def _sync_current_batch_state(self):
        """Persist current edited result back into the selected batch item."""
        return self._batch_controller.sync_current_batch_state()

    def _on_language_changed(self, language=None):
        """Apply language to all visible UI surfaces."""
        language = set_language(language or 'en')
        QSettings('QuestCut', 'QuestCut-AI').setValue('language', language)
        self.welcome_screen.retranslate_ui()
        self.editor_screen.retranslate_ui()
        self.editor_screen.filmstrip.retranslate_ui()
        self._loading_overlay.retranslate_ui()
        self.setWindowTitle('QuestCut-AI')
        self._update_gpu_status()

    def _update_gpu_status(self, *args):
        """Refresh GPU/CPU status controls."""
        from ..core.model_manager import get_model_manager
        manager = get_model_manager()
        status = manager.device_status()
        self.editor_screen.control_panel.set_gpu_controls(
            requested=manager.gpu_requested,
            available=manager.gpu_available,
            active=status.get('mode') == 'gpu',
            failed=status.get('mode') == 'fallback',
            status_text=status.get('title', ''),
            detail_text=status.get('detail', ''),
        )

    def _on_gpu_toggled(self, enabled=None):
        """Switch processing between GPU and CPU."""
        from ..core.model_manager import get_model_manager
        manager = get_model_manager()
        manager.use_gpu = bool(enabled)
        QSettings('QuestCut', 'QuestCut-AI').setValue('use_gpu', bool(enabled))
        self._update_gpu_status()
        self.editor_screen.set_status(tr('GPU enabled') if manager.use_gpu else tr('CPU mode'))

    def _retry_gpu(self):
        """Retry GPU initialization after fallback."""
        from ..core.model_manager import get_model_manager
        manager = get_model_manager()
        manager.retry_gpu()
        QSettings('QuestCut', 'QuestCut-AI').setValue('use_gpu', True)
        self._update_gpu_status()
        self.editor_screen.set_status(tr('Retrying GPU acceleration'))

    def _setup_shortcuts(self):
        '''Setup keyboard shortcuts.'''
        QShortcut(QKeySequence.Undo, self, self._undo)
        QShortcut(QKeySequence.Redo, self, self._redo)
        QShortcut(QKeySequence('Ctrl+Y'), self, self._redo)
        QShortcut(QKeySequence.Save, self, self._quick_save)
        space_shortcut = QShortcut(QKeySequence('Space'), self, self._toggle_view)
        space_shortcut.setContext(Qt.WidgetShortcut)
        c_shortcut = QShortcut(QKeySequence('C'), self, self._toggle_compare)
        c_shortcut.setContext(Qt.WidgetShortcut)
        help_shortcut = QShortcut(QKeySequence('?'), self, self._show_shortcuts)
        help_shortcut.setContext(Qt.ApplicationShortcut)
        help_shift_shortcut = QShortcut(QKeySequence('Shift+/'), self, self._show_shortcuts)
        help_shift_shortcut.setContext(Qt.ApplicationShortcut)
        help_f1_shortcut = QShortcut(QKeySequence.HelpContents, self, self._show_shortcuts)
        help_f1_shortcut.setContext(Qt.ApplicationShortcut)

    def keyPressEvent(self, event):
        '''Fallback for keyboard layouts/input methods that do not trigger QShortcut('?').'''
        if event.key() == Qt.Key_Question or event.text() in ('?', '？'):
            self._show_shortcuts()
            return None
        super().keyPressEvent(event)

    def _show_shortcuts(self):
        '''Show keyboard shortcuts help dialog.'''
        ShortcutsDialog.show_shortcuts(self)

    def closeEvent(self, event):
        """Handle application close with graceful shutdown."""
        try:
            self._recomposite_timer.stop()
            self._background_remover.cancel(blocking=True)
            self._portrait_mode.cancel(blocking=True)
            if self._batch_queue is not None:
                self._batch_queue.cancel(blocking=True)
        except Exception as exc:
            logger.warning("Error while closing workers: %s", exc)
        event.accept()
    def _show_welcome(self):
        '''Show the welcome screen and reset editor state.'''
        self._is_processing = False
        if self._batch_queue:
            self._batch_queue.cancel(False)
        self._original_image = None
        self._original_rgb_np = None
        self._processed_image = None
        self._current_mask = None
        self._base_mask = None
        self._pre_edge_mask = None
        self._position_scale = 1
        self._position_x = 0
        self._position_y = 0
        self._rotation = 0
        self._flip_h = False
        self._flip_v = False
        self._active_tool = 'none'
        self._reset_history()
        self._batch_mode = False
        self._batch_images.clear()
        self._batch_current_index = 0
        self._batch_processing_complete = False
        self._batch_queue = None
        self._batch_save_manager = None
        self.editor_screen.filmstrip.set_images([])
        self.editor_screen.filmstrip.hide()
        self.editor_screen.canvas.clear()
        self.editor_screen.control_panel.hide_batch_mode()
        self.stack.setCurrentIndex(0)
    def _show_editor(self):
        '''Show the editor screen.'''
        self.stack.setCurrentIndex(1)
        self.editor_screen.layout().activate()
    def _check_first_run(self):
        '''Check if this is the first run and show welcome guide.'''
        settings = QSettings('QuestCut', 'QuestCut-AI')
        has_shown_welcome = settings.value('has_shown_welcome', False, type=bool)
        if not has_shown_welcome:
            self._show_welcome_guide()
            settings.setValue('has_shown_welcome', True)

    def _show_welcome_guide(self):
        '''Show the first-run welcome guide dialog.'''
        from PySide6.QtWidgets import QDialog, QTextBrowser
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Welcome to QuestCut-AI!'))
        dialog.setFixedSize(550, 450)
        dialog.setStyleSheet('\n            QDialog {\n                background-color: #1a1a1d;\n            }\n            QTextBrowser {\n                background-color: #0f0f10;\n                border: 1px solid #2a2a2f;\n                border-radius: 8px;\n                padding: 20px;\n                color: #ffffff;\n            }\n        ')
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        header = QLabel(tr('Welcome!'))
        header.setStyleSheet('\n            font-size: 24px;\n            font-weight: bold;\n            color: #ffffff;\n        ')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(f'''
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; color: #ffffff; line-height: 1.6; }}
                h3 {{ color: #4F46E5; margin-top: 16px; margin-bottom: 8px; }}
                .tip {{ background: #2a2a2f; padding: 12px; border-radius: 6px; margin: 8px 0; }}
                .highlight {{ color: #22c55e; }}
                .key {{ background: #3a3a40; padding: 2px 8px; border-radius: 4px; font-family: monospace; }}
            </style>

            <h3>1. {tr('Drop or Browse Images')}</h3>
            <div class="tip">
                {tr('Simply drop images onto the app or click to browse.')}<br>
                <span class="highlight">{tr('Select multiple files for batch processing')}</span>
            </div>

            <h3>2. {tr('Choose Your AI Model')}</h3>
            <div class="tip">
                <b>BiRefNet</b> = {tr('Best quality (products, complex edges)')}<br>
                <b>BiRefNet Portrait</b> = {tr('Tuned for people cutouts')}<br>
                <b>{tr('Portrait Mode')}</b> = {tr('Alpha matting (soft hair, transparent edges)')}
            </div>

            <h3>3. {tr('Auto-Process is ON')}</h3>
            <div class="tip">
                {tr('Images are processed automatically when dropped.')}<br>
                {tr('Toggle this off in Quick Settings if you prefer manual control.')}
            </div>

            <h3>4. {tr('Batch Processing:')}</h3>
            <div class="tip">
                {tr('Drop a folder or select 2+ images to process them all at once with automatic saving')}<br>
                <span class="highlight">{tr('Process 100+ images with automatic saving!')}</span>
            </div>

            <h3>{tr('Keyboard Shortcuts')}</h3>
            <div class="tip">
                <span class="key">Space</span> {tr('Toggle before/after view')}<br>
                <span class="key">Ctrl+S</span> {tr('Quick save')}<br>
                <span class="key">Ctrl+Z</span> {tr('Undo')}
            </div>
        ''')
        layout.addWidget(browser, 1)
        start_btn = QPushButton(tr('Get Started!'))
        start_btn.setFixedHeight(48)
        start_btn.setStyleSheet('\n            QPushButton {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4F46E5, stop:1 #7C3AED);\n                border: none;\n                border-radius: 8px;\n                color: white;\n                font-size: 16px;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,\n                    stop:0 #4338CA, stop:1 #6D28D9);\n            }\n        ')
        start_btn.clicked.connect(dialog.accept)
        layout.addWidget(start_btn)
        dialog.exec()
    def _on_files_selected(self, files = None):
        '''Handle files selected from welcome screen.'''
        if not files:
            return None
        self._current_files = list(files)
        if len(files) == 1:
            self._batch_mode = False
            if self._load_image(files[0]):
                self._show_editor()
                if self.editor_screen.control_panel.is_auto_process_enabled():
                    QTimer.singleShot(100, self._process_image)
            return None
        from .batch_config_dialog import BatchConfigDialog
        config = BatchConfigDialog.configure_batch(files, self.editor_screen.control_panel.get_selected_model(), self)
        if config is None:
            return None
        self._setup_batch_processing(files, config)
    def _setup_batch_processing(self, files = None, config = None):
        '''Setup interactive batch processing for multiple files.'''
        return self._batch_controller.setup_batch_processing(files, config)
    def _show_editor_with_filmstrip(self):
        '''Show editor screen with filmstrip for interactive batch mode.'''
        return self._batch_controller.show_editor_with_filmstrip()

    def _on_thumbnails_loading(self, loaded: int = 0, total: int = 0):
        '''Update loading overlay progress as thumbnails are generated.'''
        if total > 0:
            self._loading_overlay.update_progress(loaded / total, f"{tr('Generating thumbnails')} ({loaded}/{total})")
            return None
    def _on_thumbnails_loaded(self):
        '''Hide loading overlay when all thumbnails are ready.'''
        self._loading_overlay.hide_loading()

    def _create_batch_process_func(self, model_key = None):
        '''Create the processing function for batch mode.'''
        return self._batch_controller.create_batch_process_func(model_key)
    def _on_batch_started(self):
        '''Handle batch processing started.'''
        return self._batch_controller.on_batch_started()

    def _on_batch_item_saved(self, item=None):
        '''Handle item saved in auto-save mode.'''
        return self._batch_controller.on_batch_item_saved(item)

    def _on_batch_processing_finished(self, progress = None):
        '''Handle batch processing finished (all images processed).'''
        return self._batch_controller.on_batch_processing_finished(progress)

    def _load_image(self, file_path=None):
        """Load an image from a file path."""
        if not file_path:
            return False
        try:
            path = Path(file_path)
            if not path.is_file():
                raise FileNotFoundError(str(path))
            if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'):
                raise ValueError(f'Unsupported image format: {path.suffix}')
            with Image.open(path) as img:
                img.load()
                image = ImageOps.exif_transpose(img).copy()
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            self._current_files = [str(path)]
            self._original_image = image
            self._original_rgb_np = np.array(image.convert('RGB'))
            self._processed_image = None
            self._current_mask = None
            self._base_mask = None
            self._pre_edge_mask = None
            self._edge_undo_saved = False
            self._position_scale = 1
            self._position_x = 0
            self._position_y = 0
            self._rotation = 0
            self._flip_h = False
            self._flip_v = False
            self.editor_screen.canvas.set_image(image)
            self.editor_screen.control_panel.reset_state()
            self._reset_history()
            self.editor_screen.set_status(f"{tr('Loaded')} {path.name}")
            logger.info('Loaded image: %s', path)
            return True
        except Exception as exc:
            logger.exception('Failed to load image: %s', file_path)
            self.editor_screen.control_panel.show_error(f"{tr('Could not load image:')} {exc}")
            QMessageBox.warning(self, tr('Open Image Failed'), f"{tr('Could not load image:')}\n{exc}")
            return False

    def _process_image(self):
        """Start background removal processing."""
        if self._original_image is None:
            self.editor_screen.control_panel.show_error(tr('Open or drop an image first.'))
            return None
        if self._is_processing:
            return None
        model_key = self.editor_screen.control_panel.get_selected_model()
        try:
            self._is_processing = True
            self._push_history()
            if model_key == 'modnet':
                matte = self._portrait_mode.process(self._original_image, async_mode=False)
                self._on_portrait_finished(matte)
                return None
            self._background_remover.model_name = model_key
            self._background_remover.remove_background(self._original_image, async_mode=True)
        except Exception as exc:
            self._on_processing_error(str(exc))
        return None

    def _on_ai_finished(self, result=None, mask=None):
        """Handle AI processing completion."""
        self._is_processing = False
        if result is None:
            self._on_processing_error(tr('Background removal returned no result.'))
            return None
        try:
            if result.mode != 'RGBA':
                result = result.convert('RGBA')
            if mask is None:
                mask = result.split()[3]
            elif getattr(mask, 'mode', None) != 'L':
                mask = mask.convert('L')
            if mask.size != result.size:
                mask = mask.resize(result.size, Image.LANCZOS)
            self._processed_image = result
            self._current_mask = np.array(mask)
            self._base_mask = self._current_mask.copy()
            self._pre_edge_mask = self._current_mask.copy()
            self.editor_screen.canvas.set_result(result, animate=True)
            if self._history.mutation_pending:
                self._finish_history_mutation()
            else:
                self._mark_history_baseline()
            self.editor_screen.control_panel.show_success(tr('Background removed.'))
            logger.info('Background removal completed')
            return None
        except Exception as exc:
            self._on_processing_error(str(exc))
            return None

    def _on_model_changed(self, model_key=None):
        """Handle model selection change."""
        if model_key and model_key in MODEL_CONFIG:
            self._background_remover.model_name = model_key
            self.editor_screen.set_status(f"{tr('AI Model')}: {tr_model_display(model_key, MODEL_CONFIG[model_key].get('display_name', model_key))}")

    def _on_model_error(self, model_name=None, error=None):
        """Handle model loading error."""
        message = error if error is not None else model_name
        self._on_processing_error(f"{tr('AI Model')} error: {message}")

    def _on_processing_progress(self, progress=None):
        """Handle processing progress update."""
        self.editor_screen.control_panel.update_progress(float(progress or 0))

    def _on_processing_started(self):
        """Handle processing started."""
        self._is_processing = True
        self.editor_screen.control_panel.show_processing()
        self.editor_screen.set_status(tr('Processing...'))

    def _on_processing_error(self, error=None):
        """Handle processing error."""
        self._is_processing = False
        self._cancel_history_mutation()
        message = str(error or 'Unknown error')
        logger.error('Processing error: %s', message)
        self.editor_screen.control_panel.show_error(message)
        self.editor_screen.set_status(message)
        self._update_undo_redo_state()

    def _on_background_changed(self):
        """Recomposite with new background settings."""
        if self._history.restoring:
            return None
        if self._current_mask is None:
            return None
        self._push_history()
        self._recomposite_timer.start()

    def _on_shadow_changed(self):
        """Recomposite with new shadow settings."""
        if self._history.restoring:
            return None
        if self._current_mask is None:
            return None
        self._push_history()
        self._recomposite_timer.start()

    def _on_edge_changed(self):
        """Recomposite with new edge settings."""
        if self._history.restoring:
            return None
        if self._current_mask is None:
            return None
        self._push_history()
        self._recomposite_timer.start()

    def _on_position_changed(self):
        """Recomposite with new position."""
        if self._history.restoring:
            return None
        if self._current_mask is None:
            return None
        self._push_history()
        self._recomposite_timer.start()

    def _on_tool_changed(self, tool=None, is_remove=None):
        """Handle tool change from toolbar."""
        if tool in ("brush", "pan", "none"):
            self._active_tool = tool
            self.editor_screen.canvas.set_tool(tool)
        if tool == "brush":
            self.editor_screen.canvas.set_brush_mode(not bool(is_remove))

    def _on_brush_size_changed(self, size=None):
        """Handle brush size change."""
        if size is not None:
            self.editor_screen.canvas.set_brush_size(int(size))

    def _on_brush_stroke(self, points=None, radius=None, is_add=None):
        """Handle a brush stroke on the canvas."""
        if self._current_mask is None or not points:
            return None
        self._push_history()
        mode = BrushMode.ADD if is_add else BrushMode.REMOVE
        stroke = BrushStroke(points=points, radius=radius or 10, mode=mode)
        self._current_mask = self._mask_ops.apply_brush(self._current_mask, stroke, save_undo=False)
        self._recomposite_with_mask()

    def _on_view_toggled(self, view=None):
        """Handle view toggle (original/result)."""
        if view:
            self.editor_screen.canvas.set_view_mode(view)

    def _on_compare_toggled(self, enabled=None):
        """Handle comparison slider toggle."""
        if enabled:
            self.editor_screen.canvas.enable_comparison_slider()
        else:
            self.editor_screen.canvas.show_result()

    def _on_file_dropped(self, file_path=None):
        """Handle single file dropped on canvas."""
        self._on_files_selected([file_path] if file_path else [])

    def _on_files_dropped(self, files=None):
        """Handle multiple files dropped."""
        self._on_files_selected(files or [])

    def _auto_enhance(self):
        """Auto enhance the current result."""
        if self._original_image is None or self._current_mask is None:
            self.editor_screen.control_panel.show_error(tr('Process an image before auto-enhance.'))
            return None
        try:
            self._push_history()
            from ..processing.auto_enhance import AutoEnhance
            result = AutoEnhance().auto_enhance(self._original_image, self._current_mask, center_subject=False)
            self._current_mask = result.enhanced_mask
            self._base_mask = self._current_mask.copy()
            self._processed_image = result.enhanced_image
            self.editor_screen.canvas.set_result(result.enhanced_image, animate=False)
            self._finish_history_mutation()
            self.editor_screen.control_panel.show_success(f"{tr('Enhanced. Quality score:')} {result.quality_score:.0%}")
        except Exception as exc:
            self._on_processing_error(str(exc))

    def _smart_crop(self):
        """Smart crop to subject."""
        self._on_smart_crop()

    def _portrait_finished(self, result=None):
        """Backward-compatible alias for portrait completion."""
        self._on_portrait_finished(result)

    def _on_portrait_finished(self, result=None):
        """Handle portrait processing completion."""
        self._is_processing = False
        if result is None or self._original_image is None:
            self._on_processing_error(tr('Portrait mode returned no result.'))
            return None
        try:
            matte = result.convert('L') if getattr(result, 'mode', None) != 'L' else result
            if matte.size != self._original_image.size:
                matte = matte.resize(self._original_image.size, Image.LANCZOS)
            final = self._original_image.copy()
            final.putalpha(matte)
            self._current_mask = np.array(matte)
            self._base_mask = self._current_mask.copy()
            self._pre_edge_mask = self._current_mask.copy()
            self._processed_image = final
            self.editor_screen.canvas.set_result(final, animate=True)
            if self._history.mutation_pending:
                self._finish_history_mutation()
            else:
                self._mark_history_baseline()
            self.editor_screen.control_panel.show_success(tr('Portrait matte applied.'))
        except Exception as exc:
            self._on_processing_error(str(exc))

    def _on_reset_position(self):
        """Reset position to default."""
        if self._processed_image is None and self._current_mask is None:
            return None
        self._push_history()
        self._position_scale = 1
        self._position_x = 0
        self._position_y = 0
        self._rotation = 0
        self._flip_h = False
        self._flip_v = False
        if hasattr(self.editor_screen.control_panel, 'set_position_values'):
            self.editor_screen.control_panel.set_position_values(1, 0, 0, 0, False, False)
        self._recomposite_with_mask()

    def _calculate_smart_crop_transform(self):
        """Return a position transform that centers/fits the current mask."""
        if self._original_image is None or self._current_mask is None:
            return None
        bounds = self._mask_ops.get_mask_bounds(self._current_mask)
        if not bounds:
            return None
        x, y, width, height = bounds
        if width <= 0 or height <= 0:
            return None
        canvas_w, canvas_h = self._original_image.size
        target_fill = 0.9
        scale = min(
            (canvas_w * target_fill) / width,
            (canvas_h * target_fill) / height,
        )
        scale = max(0.1, min(3.0, scale))
        center_x = x + width / 2
        center_y = y + height / 2
        offset_x = int(round(scale * (canvas_w / 2 - center_x)))
        offset_y = int(round(scale * (canvas_h / 2 - center_y)))
        offset_x = max(-500, min(500, offset_x))
        offset_y = max(-500, min(500, offset_y))
        return (scale, offset_x, offset_y)

    def _compose_with_current_settings(self, original_image=None, mask=None):
        """Build a final RGBA image using the current control-panel settings."""
        from ..processing.background import BackgroundGenerator
        from ..processing.shadow import ShadowGenerator
        if original_image is None or mask is None:
            return None
        if original_image.mode != 'RGBA':
            original_image = original_image.convert('RGBA')
        source_mask = self._clone_mask(mask)
        edge = self.editor_screen.control_panel.get_edge_settings()
        refined = self._mask_ops.refine_edges(
            source_mask,
            sharpen=edge.get('sharpen', 0),
            expand=edge.get('expand', 0),
            feather=edge.get('feather', 0),
        )
        mask_pil = Image.fromarray(refined.astype(np.uint8), 'L')
        if mask_pil.size != original_image.size:
            mask_pil = mask_pil.resize(original_image.size, Image.LANCZOS)
        subject = original_image.copy()
        subject.putalpha(mask_pil)

        pos = self.editor_screen.control_panel.get_position_settings()
        if pos.get('flip_h'):
            subject = ImageOps.mirror(subject)
        if pos.get('flip_v'):
            subject = ImageOps.flip(subject)
        scale = max(0.01, float(pos.get('scale', 1)))
        if abs(scale - 1) > 0.001:
            subject = subject.resize((max(1, int(subject.width * scale)), max(1, int(subject.height * scale))), Image.LANCZOS)
        rotation = int(pos.get('rotation', 0))
        if rotation:
            subject = subject.rotate(rotation, expand=True, resample=Image.BICUBIC)

        fg = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
        x = (fg.width - subject.width) // 2 + int(pos.get('x', 0))
        y = (fg.height - subject.height) // 2 + int(pos.get('y', 0))
        fg.paste(subject, (x, y), subject)

        bg_type, bg_settings = self.editor_screen.control_panel.get_background_settings()
        bg_gen = BackgroundGenerator()
        if bg_type == 'solid':
            bg = bg_gen.create_solid(fg.size, bg_settings.get('color', '#ffffff'))
        elif bg_type == 'gradient':
            bg = bg_gen.create_gradient(
                fg.size,
                bg_settings.get('color1', '#2193b0'),
                bg_settings.get('color2', '#6dd5ed'),
                bg_settings.get('direction', 135),
            )
        elif bg_type == 'image' and bg_settings.get('image') is not None:
            bg = bg_gen.create_from_image(
                fg.size,
                bg_settings['image'],
                bg_settings.get('fit_mode', 'cover'),
                bg_settings.get('blur', 0),
            )
        else:
            bg = bg_gen.create_transparent(fg.size)

        shadow_settings = self.editor_screen.control_panel.get_shadow_settings()
        if shadow_settings.enabled:
            return ShadowGenerator().apply_to_image_no_expand(fg, bg, shadow_settings)
        return Image.alpha_composite(bg.convert('RGBA'), fg)

    def _recomposite_with_mask(self):
        """Recomposite the final image with current mask and settings."""
        if self._original_image is None or self._current_mask is None:
            if self._history.mutation_pending:
                self._cancel_history_mutation()
            return None
        try:
            final = self._compose_with_current_settings(self._original_image, self._current_mask)
            if final is None:
                raise RuntimeError(tr('No image to composite'))
            self._processed_image = final
            self.editor_screen.canvas.update_result_silent(final)
            self._finish_history_mutation()
        except Exception as exc:
            self._cancel_history_mutation()
            logger.exception('Failed to recomposite image')
            self.editor_screen.control_panel.show_error(f"{tr('Preview update failed:')} {exc}")

    def _quick_save(self):
        """Quick save the current image."""
        return self._export_controller.quick_save()

    def _get_batch_save_manager(self, output_dir=None):
        """Return a save manager for manual batch exports."""
        return self._export_controller.get_batch_save_manager(output_dir)

    def _queue_item_from_state(self, state=None, image=None):
        return self._export_controller.queue_item_from_state(state, image)

    def _save_current_batch_image(self):
        """Save the selected batch image."""
        return self._export_controller.save_current_batch_image()

    def _save_all_batch_images(self):
        """Save every processed/edited batch image."""
        return self._export_controller.save_all_batch_images()

    def _apply_current_settings_to_all(self):
        """Apply current panel settings to all processed batch images."""
        return self._batch_controller.apply_current_settings_to_all()

    def _export_image(self):
        """Export the current image."""
        return self._export_controller.export_image()

    def _undo(self):
        """Undo last edit."""
        return self._history.undo()

    def _redo(self):
        """Redo last undone edit."""
        return self._history.redo()

    def _on_batch_item_started(self, item=None):
        """Handle batch item processing started."""
        return self._batch_controller.on_batch_item_started(item)

    def _on_batch_item_completed(self, item=None):
        """Handle batch item processing completed."""
        return self._batch_controller.on_batch_item_completed(item)

    def _on_batch_item_failed(self, item=None, error=None):
        """Handle batch item processing failed."""
        return self._batch_controller.on_batch_item_failed(item, error)

    def _on_batch_progress(self, progress=None):
        """Handle batch progress update."""
        return self._batch_controller.on_batch_progress(progress)

    def _on_smart_crop(self):
        """Handle smart crop action."""
        if self._processed_image is None or self._current_mask is None:
            self.editor_screen.control_panel.show_error(tr('Process an image before smart crop.'))
            return None
        try:
            transform = self._calculate_smart_crop_transform()
            if transform is None:
                self.editor_screen.control_panel.show_error(tr('Smart crop failed:') + ' ' + tr('No subject detected.'))
                return None
            self._push_history()
            scale, offset_x, offset_y = transform
            self.editor_screen.control_panel.set_position_values(scale, offset_x, offset_y, 0, False, False)
            self._recomposite_with_mask()
            self.editor_screen.control_panel.show_success(tr('Subject centered.'))
        except Exception as exc:
            self._cancel_history_mutation()
            self._on_processing_error(f"{tr('Smart crop failed:')} {exc}")

    def _find_batch_state(self, file_path=None):
        """Find a BatchImageState by file path."""
        return self._batch_controller.find_batch_state(file_path)

    def _on_batch_image_selected(self, image_id=None):
        """Load a selected batch image into the editor canvas."""
        return self._batch_controller.on_batch_image_selected(image_id)

    def _add_batch_images(self):
        """Add more images to the current batch list."""
        return self._batch_controller.add_batch_images()

    def _toggle_view(self):
        """Toggle between original and result view."""
        self.editor_screen.canvas.toggle_view()

    def _toggle_compare(self):
        """Toggle comparison slider."""
        self.editor_screen.canvas.enable_comparison_slider()
