"""
Batch Controller
================
Batch-processing workflow extracted from the main window while preserving UI hooks.
"""
import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..processing.batch_queue import BatchQueue
from ..processing.batch_save_manager import BatchSaveManager
from ..ui.batch_filmstrip import BatchImageState
from ..ui.batch_summary_dialog import BatchSummaryDialog
from ..utils.i18n import tr

logger = logging.getLogger(__name__)


class BatchController:
    """Coordinates batch queue setup, progress, summary, retry, and filmstrip state."""

    def __init__(self, window):
        self.window = window

    @property
    def editor_screen(self):
        return self.window.editor_screen

    def setup_batch_processing(self, files=None, config=None):
        """Setup interactive batch processing for multiple files."""
        from ..ui.batch_config_dialog import BatchConfig
        files = list(files or [])
        if not files:
            return None
        if config is None:
            config = BatchConfig(str(Path(files[0]).parent))
        self.window._batch_mode = True
        self.window._batch_processing_complete = False
        self.window._batch_config = config
        self.window._batch_output_dir = config.output_dir
        self.window._batch_start_time = None
        self.window._batch_save_manager = None
        self.window._batch_images = [BatchImageState(id=i + 1, file_path=file_path) for i, file_path in enumerate(files)]
        self.window._batch_current_index = 0
        self.window._batch_global_settings = {}
        self.show_editor_with_filmstrip()
        if config.model_key:
            self.editor_screen.control_panel.set_selected_model(config.model_key)
        if not self._ensure_batch_model_ready(config):
            return None
        self._start_queue(files, config)
        return None

    def _ensure_batch_model_ready(self, config):
        if config.model_key != 'modnet' or self.window._portrait_mode.is_model_loaded():
            return True
        if not self.window._portrait_mode.is_model_downloaded():
            reply = QMessageBox.question(
                self.window,
                tr('Download Required'),
                tr('Portrait Mode requires downloading the MODNet model (~25MiB).\nDownload now?'),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self.editor_screen.set_status(tr('Batch cancelled'))
                return False
            self.window._portrait_mode.download_model()
        self.window._portrait_mode.load_model()
        return True

    def _start_queue(self, files, config):
        self.window._batch_queue = BatchQueue()
        self.window._batch_queue.add_files(files)
        self._connect_queue(self.window._batch_queue, config)
        save_func = None
        if config.auto_save:
            self.window._batch_save_manager = BatchSaveManager(
                output_dir=config.output_dir,
                format=config.export_format,
                naming=config.naming_template,
                quality=config.quality,
            )
            save_func = self.window._batch_save_manager.save_item
        self.window._batch_queue.start(self.create_batch_process_func(config.model_key), save_func, config.auto_save, 20)

    def _connect_queue(self, queue, config):
        queue.queue_started.connect(self.on_batch_started)
        queue.queue_finished.connect(self.on_batch_processing_finished)
        queue.queue_progress.connect(self.on_batch_progress)
        queue.item_started.connect(self.on_batch_item_started)
        queue.item_completed.connect(self.on_batch_item_completed)
        queue.item_failed.connect(self.on_batch_item_failed)
        if config.auto_save and hasattr(queue, 'item_saved'):
            queue.item_saved.connect(self.on_batch_item_saved)

    def show_editor_with_filmstrip(self):
        """Show editor screen with filmstrip for interactive batch mode."""
        self.window._show_editor()
        count = len(self.window._batch_images)
        self.window._loading_overlay.show_loading(
            f"{tr('Loading')} {count} {tr('images')}...",
            tr('Generating thumbnails'),
            True,
            count <= 20,
        )
        filmstrip = self.editor_screen.filmstrip
        filmstrip.set_images(self.window._batch_images)
        filmstrip.show()
        self.editor_screen.control_panel.show_batch_mode()
        self.editor_screen.control_panel.set_batch_save_enabled(False)
        if self.window._batch_images:
            self.window._load_image(self.window._batch_images[0].file_path)

    def create_batch_process_func(self, model_key=None):
        """Create the processing function for batch mode."""
        batch_model = model_key or self.editor_screen.control_panel.get_selected_model()

        def process_file(file_path=None):
            with Image.open(file_path) as img:
                img.load()
                original = img.copy()
            if original.mode != 'RGBA':
                original = original.convert('RGBA')
            if batch_model == 'modnet':
                matte = self.window._portrait_mode._process_sync(original)
                result_image = original.copy()
                result_image.putalpha(matte)
                return result_image, matte
            return self.window._background_remover.remove_background_sync(original, batch_model)

        return process_file

    def on_batch_started(self):
        self.window._batch_start_time = time.time()
        logger.info('Batch processing started')
        self.editor_screen.set_status(tr('Processing images...'))
        self.editor_screen.control_panel.set_batch_processing_active(True, len(self.window._batch_images))

    def on_batch_item_saved(self, item=None):
        state = self.find_batch_state(getattr(item, 'file_path', None))
        if state is not None:
            state.status = 'saved'
            state.saved_path = getattr(item, 'saved_path', '')
        self.editor_screen.filmstrip.refresh_all()

    def on_batch_processing_finished(self, progress=None):
        if progress is None:
            return None
        self.window._batch_processing_complete = True
        logger.info('Batch processing finished: %s completed, %s failed', progress.completed, progress.failed)
        self.editor_screen.control_panel.set_batch_processing_active(False)
        self.editor_screen.filmstrip.release_processed_images()
        if hasattr(self.window, '_filmstrip_refresh_timer') and self.window._filmstrip_refresh_timer.isActive():
            self.window._filmstrip_refresh_timer.stop()
        self.editor_screen.filmstrip.refresh_all()
        self.editor_screen.control_panel.set_batch_save_enabled(True)
        msg = f"{tr('All images processed!')} {progress.completed} {tr('ready')}"
        if progress.failed > 0:
            msg += f" ({progress.failed} {tr('failed')})"
        self.editor_screen.set_status(msg)
        self._show_summary_dialog(progress)
        return None

    def _show_summary_dialog(self, progress):
        elapsed = 0
        if self.window._batch_start_time:
            elapsed = max(0, time.time() - self.window._batch_start_time)
        save_stats = self.window._batch_save_manager.get_statistics() if self.window._batch_save_manager else None
        dialog = BatchSummaryDialog(
            progress=progress,
            batch_images=self.window._batch_images,
            output_dir=self.window._batch_output_dir,
            elapsed_time=elapsed,
            save_stats=save_stats,
            parent=self.window,
        )
        dialog.retry_failed.connect(self.retry_failed)
        dialog.open_folder.connect(self.open_output_folder)
        dialog.process_more.connect(self.add_batch_images)
        self.window._batch_summary_dialog = dialog
        dialog.show()
        return dialog

    def retry_failed(self):
        failed_states = [state for state in self.window._batch_images if state.has_error]
        if not failed_states:
            self.editor_screen.control_panel.show_success(tr('No failed items to retry.'))
            return None
        config = self.window._batch_config
        if config is None:
            return None
        if not self._ensure_batch_model_ready(config):
            return None
        for state in failed_states:
            state.status = 'pending'
            state.error_message = ''
            state.thumbnail = None
        self.window._batch_processing_complete = False
        self.window._batch_start_time = None
        self.editor_screen.control_panel.set_batch_save_enabled(False)
        self._start_queue([state.file_path for state in failed_states], config)
        self.editor_screen.filmstrip.refresh_all()
        return None

    def open_output_folder(self):
        output_dir = self.window._batch_output_dir
        if output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output_dir))))

    def on_batch_item_started(self, item=None):
        state = self.find_batch_state(getattr(item, 'file_path', None))
        if state is not None:
            state.status = 'processing'
        self.editor_screen.set_status(f"{tr('Processing')} {Path(item.file_path).name if item else tr('image')}...")
        self.editor_screen.filmstrip.refresh_all()

    def on_batch_item_completed(self, item=None):
        state = self.find_batch_state(getattr(item, 'file_path', None))
        if state is not None:
            state.status = 'saved' if getattr(item, 'saved_path', '') else 'processed'
            state.processed_image = getattr(item, 'result_image', None)
            state.result_mask = getattr(item, 'result_mask', None)
            state.saved_path = getattr(item, 'saved_path', '')
            state.error_message = ''
            state.thumbnail = None
        self.editor_screen.filmstrip.refresh_all()

    def on_batch_item_failed(self, item=None, error=None):
        state = self.find_batch_state(getattr(item, 'file_path', None))
        if state is not None:
            state.status = 'error'
            state.error_message = str(error or getattr(item, 'error_message', 'Unknown error'))
        self.editor_screen.set_status(f"{tr('Failed:')} {Path(item.file_path).name if item else tr('image')}")
        self.editor_screen.filmstrip.refresh_all()

    def on_batch_progress(self, progress=None):
        if progress is None:
            return None
        self.editor_screen.control_panel.update_batch_info(
            processed=progress.completed + progress.failed + progress.skipped,
            total=progress.total,
            edited=sum(1 for img in self.window._batch_images if img.has_custom_edits),
            saved=getattr(progress, 'saved', 0),
        )

    def find_batch_state(self, file_path=None):
        if not file_path:
            return None
        target = str(Path(file_path))
        for state in self.window._batch_images:
            if str(Path(state.file_path)) == target:
                return state
        return None

    def sync_current_batch_state(self):
        if not self.window._batch_mode or not self.window._batch_images:
            return None
        if not (0 <= self.window._batch_current_index < len(self.window._batch_images)):
            return None
        state = self.window._batch_images[self.window._batch_current_index]
        if self.window._processed_image is not None:
            state.processed_image = self.window._processed_image.copy()
            if self.window._current_mask is not None:
                state.result_mask = Image.fromarray(self.window._current_mask.astype(np.uint8), 'L')
            state.has_custom_edits = True
            if state.status in ('processed', 'saved'):
                state.status = 'edited'
            state.thumbnail = None
            self.editor_screen.filmstrip.refresh_all()
        else:
            state.processed_image = None
            state.result_mask = None
            state.thumbnail = None
            if state.status in ('processed', 'edited', 'saved'):
                state.status = 'pending'
            self.editor_screen.filmstrip.refresh_all()
        return None

    def on_batch_image_selected(self, image_id=None):
        """Load a selected batch image into the editor canvas."""
        for i, state in enumerate(self.window._batch_images):
            if state.id != image_id:
                continue
            self.window._batch_current_index = i
            if state.processed_image is not None:
                with Image.open(state.file_path) as img:
                    img.load()
                    original = ImageOps.exif_transpose(img).convert('RGBA')
                self.window._original_image = original
                self.window._original_rgb_np = np.array(original.convert('RGB'))
                self.window._current_files = [state.file_path]
                self.editor_screen.canvas.set_image(original)
                self.window._processed_image = state.processed_image.copy()
                self.editor_screen.canvas.set_result(self.window._processed_image, animate=False)
                self._restore_mask_from_state(state, original)
                self.window._mark_history_baseline()
            else:
                self.window._load_image(state.file_path)
            return None
        return None

    def _restore_mask_from_state(self, state, original):
        if state.result_mask is not None:
            mask = state.result_mask.convert('L') if getattr(state.result_mask, 'mode', None) != 'L' else state.result_mask
            if mask.size != original.size:
                mask = mask.resize(original.size, Image.LANCZOS)
            self.window._current_mask = np.array(mask)
            self.window._base_mask = self.window._current_mask.copy()
            self.window._pre_edge_mask = self.window._current_mask.copy()
            return None
        if self.window._processed_image.mode == 'RGBA':
            self.window._current_mask = np.array(self.window._processed_image.split()[3])
            self.window._base_mask = self.window._current_mask.copy()
            self.window._pre_edge_mask = self.window._current_mask.copy()
            return None
        self.window._current_mask = None
        self.window._base_mask = None
        self.window._pre_edge_mask = None

    def add_batch_images(self, files=None):
        if files is None or files is False:
            files, _ = QFileDialog.getOpenFileNames(
                self.window,
                tr('Add Images'),
                '',
                tr('Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif)'),
            )
        if not files:
            return None
        start = len(self.window._batch_images)
        for offset, file_path in enumerate(files, start=1):
            self.window._batch_images.append(BatchImageState(id=start + offset, file_path=file_path))
        self.editor_screen.filmstrip.set_images(self.window._batch_images)
        return None

    def apply_current_settings_to_all(self):
        if not self.window._batch_mode or not self.window._batch_images:
            return None
        self.sync_current_batch_state()
        updated = 0
        for state in self.window._batch_images:
            if state.result_mask is None:
                continue
            try:
                with Image.open(state.file_path) as img:
                    img.load()
                    original = ImageOps.exif_transpose(img).convert('RGBA')
                mask = state.result_mask.convert('L') if getattr(state.result_mask, 'mode', None) != 'L' else state.result_mask
                if mask.size != original.size:
                    mask = mask.resize(original.size, Image.LANCZOS)
                composed = self.window._compose_with_current_settings(original, np.array(mask))
                if composed is None:
                    continue
                state.processed_image = composed
                state.has_custom_edits = True
                state.status = 'edited'
                state.saved_path = ''
                state.thumbnail = None
                updated += 1
            except OSError as exc:
                logger.warning('Failed to apply settings to %s: %s', state.file_path, exc)
                state.status = 'error'
                state.error_message = str(exc)
        if self.window._batch_images:
            current_id = self.window._batch_images[self.window._batch_current_index].id
            self.on_batch_image_selected(current_id)
        self.editor_screen.filmstrip.refresh_all()
        self.editor_screen.control_panel.show_success(f"{tr('Applied to')} {updated} {tr('images')}")
        return updated
