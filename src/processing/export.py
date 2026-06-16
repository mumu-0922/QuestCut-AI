'''
Export Manager for QuestCut-AI
==========================
Image export in various formats and social media sizes.
'''
import logging
import os
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from PIL import Image
from PySide6.QtCore import QObject, Signal, QThread
from ..utils.constants import EXPORT_FORMATS, PLATFORM_SIZES, RESOLUTION_PRESETS
from .transform import ImageTransform
logger = logging.getLogger(__name__)
@dataclass
class ExportSettings:
    filename_template: str = '{original}_{platform}'
    include_timestamp: bool = False
    format: str = 'PNG'
    quality: int = 95

    def get_extension(self):
        return f'.{self.format.lower()}'


@dataclass
class ExportResult:
    success: bool = False
    error: str = ''
    output_path: str = ''


@dataclass
class BulkExportProgress:
    current: int = 0
    total: int = 0
    current_file: str = ''
    completed: list = field(default_factory=list)
class ExportWorker(QThread):
    '''Worker thread for export operations.'''
    progress = Signal(object)
    finished = Signal(list)
    def __init__(self, images = None, output_dir = None, settings = None, platforms = None, parent = None):
        super().__init__(parent)
        self.images = images
        self.output_dir = output_dir
        self.settings = settings
        self.platforms = platforms
        self._cancelled = False
    def run(self):
        results = []
        total = len(self.images)
        if self.platforms:
            total *= len(self.platforms)
        for image, original_name in self.images:
            if self._cancelled:
                break
            if self.platforms:
                for platform in self.platforms:
                    if self._cancelled:
                        break
                    progress = BulkExportProgress(current=len(results) + 1, total=total, current_file=f'''{original_name} ({platform})''', completed=results.copy())
                    self.progress.emit(progress)
                    result = export_for_platform(image, platform, self.output_dir, original_name, self.settings)
                    results.append(result)
            else:
                progress = BulkExportProgress(current=len(results) + 1, total=total, current_file=original_name, completed=results.copy())
                self.progress.emit(progress)
                result = export_single(image, self.output_dir, original_name, self.settings)
                results.append(result)
        if self._cancelled:
            results.append(ExportResult(success=False, error='Export cancelled by user'))
        self.finished.emit(results)
    def cancel(self):
        self._cancelled = True
class ExportManager(QObject):
    '''
    Manages image export operations.
    Supports various formats, quality settings, and social media
    platform sizing with organized folder output.
    '''
    export_started = Signal()
    export_progress = Signal(object)
    export_finished = Signal(list)
    export_error = Signal(str)
    def __init__(self, parent = None):
        super().__init__(parent)
        self._worker = None
        self._transform = ImageTransform()
    def export(self, image = None, output_path = None, settings = None):
        '''
        Export single image.
        Args:
            image: Image to export
            output_path: Full output path
            settings: Export settings
        Returns:
            ExportResult
        '''
        if not settings:
            settings = ExportSettings()
        if image is None:
            return ExportResult(success=False, error='No image provided')
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path)
            return ExportResult(success=True, output_path=output_path)
        except Exception as e:
            return ExportResult(success=False, error=str(e))
    def export_for_platform(self, image = None, platform = None, output_dir = None, original_filename = None, settings = None):
        """
        Export image sized for a specific platform.
        Args:
            image: Image to export
            platform: Platform key (e.g., 'instagram_square')
            output_dir: Base output directory
            original_filename: Original filename for naming
      settings: Export settings
        Returns:
            ExportResult
        """
        if not settings:
            settings = ExportSettings()
        platform_config = PLATFORM_SIZES.get(platform)
        if platform_config is None:
            return ExportResult(success=False, error=f'''Unknown platform: {platform}''')
        target_size = (platform_config['width'], platform_config['height'])
        fitted = self._transform.fit_to_canvas(image, target_size, fit_mode='contain', position='center')
        folder = platform_config.get('folder', platform)
        filename = self._build_filename(original_filename, settings, platform_config['name'])
        output_path = os.path.join(output_dir, folder, filename)
        return self.export(fitted, output_path, settings)
    def export_all_platforms(self, image, output_dir = None, original_filename = None, platforms = None, settings = None, async_mode = False):
        '''
        Export image for multiple platforms.
        Args:
            image: Image to export
            output_dir: Base output directory
            original_filename: Original filename
            platforms: List of platform keys, or None for all
            settings: Export settings
            async_mode: Run in background thread
        Returns:
            If async_mode=False: List of ExportResult
            If async_mode=True: None (results via signals)
        '''
        if platforms is None:
            platforms = list(PLATFORM_SIZES.keys())
        if not settings:
            settings = ExportSettings()
        if async_mode:
            self.cancel()
            self._worker = ExportWorker(images=[(image, original_filename)], output_dir=output_dir, settings=settings, platforms=platforms, parent=self)
            self._worker.progress.connect(self.export_progress.emit)
            self._worker.finished.connect(self._on_worker_finished)
            self.export_started.emit()
            self._worker.start()
            return None
        results = []
        for platform in platforms:
            result = self.export_for_platform(image, platform, output_dir, original_filename, settings)
            results.append(result)
        return results
    def bulk_export(self, images = None, output_dir = None, settings = None, platforms = None):
        '''
        Export multiple images.
        Args:
            images: List of (image, original_filename) tuples
            output_dir: Output directory
            settings: Export settings
            platforms: Optional platform list for sized exports
        '''
        self.cancel()
        if not settings:
            settings = ExportSettings()
        self._worker = ExportWorker(images=images, output_dir=output_dir, settings=settings, platforms=platforms, parent=self)
        self._worker.progress.connect(self.export_progress.emit)
        self._worker.finished.connect(self._on_worker_finished)
        self.export_started.emit()
        self._worker.start()
    def _on_worker_finished(self, results = None):
        '''Handle worker completion.'''
        self._worker = None
        self.export_finished.emit(results)
    def _build_filename(self, original = None, settings = None, platform_name = None):
        '''Build output filename from template.'''
        base = Path(original).stem
        filename = settings.filename_template
        filename = filename.replace('{original}', base)
        if platform_name:
            if '{platform}' in filename:
                filename = filename.replace('{platform}', platform_name)
            else:
                safe_name = platform_name.replace(' ', '_').replace('×', 'x')
                filename = f'''{filename}_{safe_name}'''
        elif '{platform}' in filename:
            filename = filename.replace('{platform}', '')
            filename = filename.replace('__', '_').strip('_')
        if settings.include_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = filename.replace('{timestamp}', timestamp)
        elif '{timestamp}' in filename:
            filename = filename.replace('{timestamp}', '')
            filename = filename.replace('__', '_').strip('_')
        filename += settings.get_extension()
        return filename
    def cancel(self):
        '''Cancel current export operation.'''
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
            self._worker = None
            return None
    def is_exporting(self):
        """Check if currently exporting."""
        if self._worker is not None:
            return self._worker.isRunning()
        return False

    @staticmethod
    def get_formats():
        """Get available export formats."""
        return EXPORT_FORMATS.copy()

    @staticmethod
    def get_platforms():
        """Get available platform sizes."""
        return PLATFORM_SIZES.copy()

    @staticmethod
    def get_resolution_presets():
        """Get resolution scale presets."""
        return RESOLUTION_PRESETS.copy()
def export_single(image=None, output_dir=None, original_filename=None, settings=None):
    """Export a single image. Convenience function."""
    manager = ExportManager()
    if settings is None:
        settings = ExportSettings()
    return manager.export(image, os.path.join(output_dir, original_filename), settings)


def export_for_platform(image=None, output_dir=None, original_filename=None, platform=None, settings=None):
    """Export an image sized for a specific platform. Convenience function."""
    manager = ExportManager()
    if settings is None:
        settings = ExportSettings()
    return manager.export_for_platform(image, platform, output_dir, original_filename, settings)
