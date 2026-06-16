'''
Progressive Preview for QuestCut-AI
================================
Shows low-resolution preview quickly, then swaps to full-resolution.
'''
import logging
from typing import Optional, Callable, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, Signal, QThread
logger = logging.getLogger(__name__)
@dataclass
class PreviewResult:
    image: Optional[Image.Image] = None
    mask: Optional[np.ndarray] = None
class PreviewWorker(QThread):
    '''Worker thread for generating preview.'''
    finished = Signal(object)
    def __init__(self, image = None, process_func = None, preview_size = None, is_preview = None, parent = None):
        super().__init__(parent)
        self.image = image
        self.process_func = process_func
        self.preview_size = preview_size
        self.is_preview = is_preview
        self._cancelled = False
    def run(self):
        if self._cancelled:
            return
        if self.is_preview:
            resized = self._resize_for_preview(self.image)
        else:
            resized = self.image
        result = self.process_func(resized)
        self.finished.emit(result)
    def _resize_for_preview(self, image = None):
        '''Resize image for preview processing.'''
        (width, height) = image.size
        max_dim = max(width, height)
        if max_dim <= self.preview_size:
            return image
        scale = self.preview_size / max_dim
        new_size = (int(width * scale), int(height * scale))
        return image.resize(new_size, Image.BILINEAR)
    def cancel(self):
        self._cancelled = True
class ProgressivePreview(QObject):
    '''
    Progressive preview system.
    Shows low-resolution preview immediately while processing
    full resolution in background.
    Usage:
        preview = ProgressivePreview()
        preview.preview_ready.connect(on_preview)
        preview.full_ready.connect(on_full)
        preview.process(image, remove_background_func)
    '''
    preview_ready = Signal(object)
    full_ready = Signal(object)
    progress = Signal(str, float)
    error = Signal(str)
    DEFAULT_PREVIEW_SIZE = 320
    MEDIUM_PREVIEW_SIZE = 640
    def __init__(self, preview_size = None, parent = None):
        super().__init__(parent)
        self.preview_size = preview_size
        self._preview_worker = None
        self._full_worker = None
        self._current_image = None
        self._process_func = None
    def process(self, image = None, process_func = None, skip_preview = False):
        '''
        Start progressive processing.
        Args:
            image: Image to process
            process_func: Function that takes image and returns (result, mask)
            skip_preview: Skip preview and go straight to full resolution
        '''
        self.cancel()
        self._current_image = image
        self._process_func = process_func
        max_dim = max(image.size)
        if skip_preview or max_dim <= self.preview_size * 1.5:
            self._start_full_processing()
            return None
        self._start_preview_processing()
    def _start_preview_processing(self):
        '''Start preview processing.'''
        self.progress.emit('preview', 0)
        self._preview_worker = PreviewWorker(image=self._current_image, process_func=self._process_func, preview_size=self.preview_size, is_preview=True, parent=self)
        self._preview_worker.finished.connect(self._on_preview_finished)
        self._preview_worker.start()
    def _start_full_processing(self):
        '''Start full resolution processing.'''
        self.progress.emit('full', 0)
        self._full_worker = PreviewWorker(image=self._current_image, process_func=self._process_func, preview_size=0, is_preview=False, parent=self)
        self._full_worker.finished.connect(self._on_full_finished)
        self._full_worker.start()
    def _on_preview_finished(self, result = None):
        '''Handle preview completion.'''
        sender = self.sender()
        if sender is not self._preview_worker:
            if sender is not None:
                sender.deleteLater()
            return None
        self._preview_worker = None
        if result:
            self.progress.emit('preview', 1)
            self.preview_ready.emit(result)
        else:
            logger.warning('Preview processing failed, attempting full resolution')
        self._start_full_processing()
    def _on_full_finished(self, result = None):
        '''Handle full resolution completion.'''
        sender = self.sender()
        if sender is not self._full_worker:
            if sender is not None:
                sender.deleteLater()
            return None
        self._full_worker = None
        self._current_image = None
        self._process_func = None
        if result:
            self.progress.emit('full', 1)
            self.full_ready.emit(result)
            return None
        self.error.emit('Full resolution processing failed')
    def cancel(self):
        '''Cancel all processing.'''
        if self._preview_worker:
            self._preview_worker.cancel()
            self._preview_worker.wait(2000)
            self._preview_worker = None
        if self._full_worker:
            self._full_worker.cancel()
            self._full_worker.wait(2000)
            self._full_worker = None
            return None
    def is_processing(self):
        '''Check if currently processing.'''
        return (self._preview_worker is not None and self._preview_worker.isRunning()) or (self._full_worker is not None and self._full_worker.isRunning())
    def is_preview_processing(self):
        '''Check if preview is processing.'''
        return self._preview_worker is not None and self._preview_worker.isRunning()
    def is_full_processing(self):
        '''Check if full resolution is processing.'''
        return self._full_worker is not None and self._full_worker.isRunning()
