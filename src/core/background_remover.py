"""
Background Remover for QuestCut-AI
================================
AI-powered background removal using rembg (BiRefNet).
"""
import logging
import threading
from typing import Optional, Tuple
from PIL import Image
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread
from .model_manager import get_model_manager, ModelManager
from ..utils.constants import MODEL_CONFIG
logger = logging.getLogger(__name__)


def _extract_result_mask(result):
    if result.mode == "RGBA":
        return result.split()[3]
    return Image.new("L", result.size, 255)

def _remove_with_cpu_fallback(manager, image, session, **kwargs):
    import rembg
    try:
        return rembg.remove(image, session=session, **kwargs)
    except Exception as exc:
        if manager.use_gpu and ModelManager.is_gpu_runtime_error(exc):
            logger.warning("GPU inference failed; retrying on CPU: %s", exc)
            model_name = getattr(manager, 'rembg_model_name', None)
            manager._mark_gpu_runtime_failed(exc)
            if not model_name or not manager.load_rembg_model(model_name):
                raise
            cpu_session = manager.get_rembg_session()
            return rembg.remove(image, session=cpu_session, **kwargs)
        raise
class RemovalWorker(QThread):
    progress = Signal(float)
    finished = Signal(object, object)
    def __init__(self, image, model_name, alpha_matting=False,
                 alpha_matting_foreground_threshold=240,
                 alpha_matting_background_threshold=10, parent=None):
        super().__init__(parent)
        self.image = image
        self.model_name = model_name
        self.alpha_matting = alpha_matting
        self.alpha_matting_foreground_threshold = alpha_matting_foreground_threshold
        self.alpha_matting_background_threshold = alpha_matting_background_threshold
        self._cancelled = False
    def run(self):
        relay = None
        manager = None
        try:
            self.progress.emit(0.02)
            manager = get_model_manager()

            def relay(model_name, progress):
                if model_name == self.model_name and not self._cancelled:
                    self.progress.emit(float(progress or 0))

            try:
                manager.model_loading.connect(relay)
            except Exception:
                relay = None

            if not manager.load_rembg_model(self.model_name):
                self.finished.emit(None, f"Failed to load model: {self.model_name}")
                return
            if self._cancelled:
                self.finished.emit(None, "Cancelled")
                return
            self.progress.emit(0.25)
            session = manager.get_rembg_session()
            import rembg
            self.progress.emit(0.35)
            result = _remove_with_cpu_fallback(
                manager, self.image, session,
                alpha_matting=self.alpha_matting,
                alpha_matting_foreground_threshold=self.alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=self.alpha_matting_background_threshold,
                only_mask=False)
            if self._cancelled:
                self.finished.emit(None, "Cancelled")
                return
            mask = _extract_result_mask(result)
            self.progress.emit(1.0)
            self.finished.emit(result, mask)
        except Exception as e:
            self.finished.emit(None, str(e))
        finally:
            if manager is not None and relay is not None:
                try:
                    manager.model_loading.disconnect(relay)
                except Exception:
                    pass
    def cancel(self):
        self._cancelled = True
class BackgroundRemover(QObject):
    processing_started = Signal()
    processing_progress = Signal(float)
    processing_finished = Signal(object, object)
    processing_error = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._current_model = "birefnet"
        self._sync_lock = threading.Lock()
    @property
    def model_name(self):
        return self._current_model
    @model_name.setter
    def model_name(self, value):
        if value in MODEL_CONFIG and "rembg_model" in MODEL_CONFIG[value]:
            self._current_model = value
        else:
            logger.warning(f"Unknown model: {value}, using birefnet")
            self._current_model = "birefnet"
    def remove_background(self, image, alpha_matting=False,
                          alpha_matting_foreground_threshold=240,
                          alpha_matting_background_threshold=10,
                          async_mode=True):
        self.cancel()
        if async_mode:
            self._worker = RemovalWorker(
                image, self._current_model, alpha_matting,
                alpha_matting_foreground_threshold,
                alpha_matting_background_threshold, self)
            self._worker.progress.connect(self.processing_progress.emit)
            self._worker.finished.connect(self._on_worker_finished)
            self.processing_started.emit()
            self._worker.start()
            return None
        manager = get_model_manager()
        if not manager.load_rembg_model(self._current_model):
            raise RuntimeError(f"Failed to load model: {self._current_model}")
        session = manager.get_rembg_session()
        result = _remove_with_cpu_fallback(
            manager, image, session, alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            only_mask=False)
        mask = _extract_result_mask(result)
        return (result, mask)
    def _on_worker_finished(self, result, mask_or_error):
        sender = self.sender()
        was_cancelled = getattr(sender, "_cancelled", False)
        self._worker = None
        if sender is not None:
            sender.deleteLater()
        if was_cancelled:
            return
        if result is None:
            error_msg = str(mask_or_error) if mask_or_error else "Unknown error"
            self.processing_error.emit(error_msg)
        else:
            self.processing_finished.emit(result, mask_or_error)
    def get_mask_only(self, image, alpha_matting=False):
        manager = get_model_manager()
        if not manager.load_rembg_model(self._current_model):
            raise RuntimeError(f"Failed to load model: {self._current_model}")
        session = manager.get_rembg_session()
        mask = _remove_with_cpu_fallback(
            manager, image, session, alpha_matting=alpha_matting,
            only_mask=True)
        return mask
    def cancel(self, blocking=False):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            if blocking:
                if not self._worker.wait(5000):
                    logger.warning("Worker did not finish within timeout, forcing termination")
                    self._worker.terminate()
                    self._worker.wait(1000)
                self._worker = None
    def is_processing(self):
        return self._worker is not None and self._worker.isRunning()
    def remove_background_sync(self, image, model_name=None, alpha_matting=False,
                               alpha_matting_foreground_threshold=240,
                               alpha_matting_background_threshold=10):
        use_model = model_name if (model_name and model_name in MODEL_CONFIG
                                   and "rembg_model" in MODEL_CONFIG[model_name]) else self._current_model
        manager = get_model_manager()
        if not manager.load_rembg_model(use_model):
            raise RuntimeError(f"Failed to load model: {use_model}")
        session = manager.get_rembg_session()
        result = _remove_with_cpu_fallback(
            manager, image, session, alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            only_mask=False)
        mask = _extract_result_mask(result)
        return (result, mask)
    @staticmethod
    def get_available_models():
        models = {}
        for key, config in MODEL_CONFIG.items():
            if "rembg_model" in config:
                models[key] = {
                    "name": config["name"],
                    "display_name": config["display_name"],
                    "description": config.get("description", ""),
                    "size": config.get("size", "Unknown")}
        return models
def remove_background_simple(image, model_name="birefnet"):
    remover = BackgroundRemover()
    remover.model_name = model_name
    return remover.remove_background(image, async_mode=False)
