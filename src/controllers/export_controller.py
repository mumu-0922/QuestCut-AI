"""
Export Controller
=================
Save/export workflows extracted from the main window without changing public UI hooks.
"""
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QProgressDialog

from ..processing.batch_queue import QueueItem
from ..processing.batch_save_manager import BatchSaveManager
from ..utils.i18n import tr


class ExportController:
    """Coordinates quick save, single export, and manual batch export flows."""

    def __init__(self, window):
        self.window = window

    @property
    def editor_screen(self):
        return self.window.editor_screen

    def quick_save(self):
        """Quick save the current image beside the source file."""
        if self.window._processed_image is None:
            self.editor_screen.control_panel.show_error(tr('Nothing to save. Remove background first.'))
            return None
        try:
            source = Path(self.window._current_files[0]) if self.window._current_files else Path('questcut.png')
            output = source.with_name(f'{source.stem}_nobg.png')
            counter = 1
            while output.exists():
                output = source.with_name(f'{source.stem}_nobg_{counter}.png')
                counter += 1
            self.window._processed_image.save(output, 'PNG', optimize=True)
            self.editor_screen.control_panel.show_success(f"{tr('Saved')} {output.name}")
            self.editor_screen.set_status(f"{tr('Saved:')} {output}")
            return str(output)
        except (OSError, RuntimeError, ValueError) as exc:
            self.window._on_processing_error(f"{tr('Save failed:')} {exc}")
            return None

    def get_batch_save_manager(self, output_dir=None):
        """Return a save manager for manual batch exports."""
        if output_dir is None:
            output_dir = self.window._batch_output_dir
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self.window, tr('Select Output Directory'))
            if not output_dir:
                return None
            self.window._batch_output_dir = output_dir
        config = self.window._batch_config
        fmt = getattr(config, 'export_format', 'png') if config is not None else 'png'
        naming = getattr(config, 'naming_template', '{original}_nobg') if config is not None else '{original}_nobg'
        quality = getattr(config, 'quality', 90) if config is not None else 90
        return BatchSaveManager(output_dir=output_dir, format=fmt, naming=naming, quality=quality)

    @staticmethod
    def queue_item_from_state(state=None, image=None):
        item = QueueItem(file_path=getattr(state, 'file_path', ''))
        item.result_image = image if image is not None else getattr(state, 'processed_image', None)
        item.result_mask = getattr(state, 'result_mask', None)
        return item

    def save_current_batch_image(self):
        """Save the selected batch image."""
        if not self.window._batch_mode or not self.window._batch_images:
            return self.quick_save()
        if not (0 <= self.window._batch_current_index < len(self.window._batch_images)):
            return None
        self.window._sync_current_batch_state()
        state = self.window._batch_images[self.window._batch_current_index]
        if state.processed_image is None:
            self.editor_screen.control_panel.show_error(tr('Nothing to save. Remove background first.'))
            return None
        manager = self.get_batch_save_manager()
        if manager is None:
            return None
        try:
            saved_path = manager.save_item(self.queue_item_from_state(state))
            if not saved_path:
                raise RuntimeError(tr('Save failed:'))
            state.saved_path = saved_path
            state.status = 'saved'
            state.thumbnail = None
            self.editor_screen.filmstrip.refresh_all()
            self.editor_screen.control_panel.show_success(f"{tr('Saved')} {Path(saved_path).name}")
            self.editor_screen.set_status(f"{tr('Saved:')} {saved_path}")
            return saved_path
        except (OSError, RuntimeError, ValueError) as exc:
            self.window._on_processing_error(f"{tr('Save failed:')} {exc}")
            return None

    def save_all_batch_images(self):
        """Save every processed/edited batch image."""
        if not self.window._batch_mode or not self.window._batch_images:
            return self.quick_save()
        self.window._sync_current_batch_state()
        manager = self.get_batch_save_manager()
        if manager is None:
            return None
        saved = 0
        skipped = 0
        try:
            progress = QProgressDialog(tr('Saving batch images...'), tr('Cancel'), 0, len(self.window._batch_images), self.window)
            progress.setWindowTitle(tr('Save All Images'))
            progress.setWindowModality(Qt.WindowModal)
            for index, state in enumerate(self.window._batch_images):
                progress.setValue(index)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
                image = state.processed_image
                if image is None or state.result_mask is None:
                    skipped += 1
                    continue
                saved_path = manager.save_item(self.queue_item_from_state(state, image))
                if saved_path:
                    state.saved_path = saved_path
                    state.status = 'saved'
                    state.thumbnail = None
                    saved += 1
                else:
                    skipped += 1
            progress.setValue(len(self.window._batch_images))
            self.editor_screen.filmstrip.refresh_all()
            self.editor_screen.control_panel.update_batch_info(
                processed=sum(1 for img in self.window._batch_images if img.is_processed),
                total=len(self.window._batch_images),
                edited=sum(1 for img in self.window._batch_images if img.has_custom_edits),
                saved=sum(1 for img in self.window._batch_images if getattr(img, 'saved_path', '')),
            )
            message = f"{tr('Saved')} {saved}/{len(self.window._batch_images)}"
            if skipped:
                message += f" • {tr('Skipped')} {skipped}"
            self.editor_screen.control_panel.show_success(message)
            self.editor_screen.set_status(f"{tr('Saved:')} {manager.output_dir}")
            return saved
        except (OSError, RuntimeError, ValueError) as exc:
            self.window._on_processing_error(f"{tr('Save failed:')} {exc}")
            return None

    def export_image(self):
        """Export the current image to a user-selected path."""
        if self.window._processed_image is None:
            self.editor_screen.control_panel.show_error(tr('Nothing to export. Remove background first.'))
            return None
        settings = self.editor_screen.control_panel.get_export_settings()
        ext = settings.get_extension()
        source = Path(self.window._current_files[0]) if self.window._current_files else Path('questcut')
        default_name = str(source.with_name(f'{source.stem}_export{ext}'))
        file_path, _ = QFileDialog.getSaveFileName(
            self.window,
            tr('Export'),
            default_name,
            tr('PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp)')
        )
        if not file_path:
            return None
        try:
            output = Path(file_path)
            img = self.window._processed_image
            suffix = output.suffix.lower()
            if suffix in ('.jpg', '.jpeg'):
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(output, 'JPEG', quality=settings.quality, optimize=True)
            elif suffix == '.webp':
                img.save(output, 'WEBP', quality=settings.quality)
            else:
                img.save(output, 'PNG', optimize=True)
            self.editor_screen.control_panel.show_success(f"{tr('Exported')} {output.name}")
            self.editor_screen.set_status(f"{tr('Exported:')} {output}")
            return str(output)
        except (OSError, RuntimeError, ValueError) as exc:
            self.window._on_processing_error(f"{tr('Export failed:')} {exc}")
            return None
