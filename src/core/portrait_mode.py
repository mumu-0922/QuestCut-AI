'''
Portrait Mode for QuestCut-AI
=========================
Hair and portrait matting using MODNet ONNX model.
'''
import logging
from typing import Optional, Tuple
import numpy as np
from PIL import Image
from PySide6.QtCore import QObject, Signal, QThread
from .model_manager import get_model_manager, ModelManager
logger = logging.getLogger(__name__)
MODNET_INPUT_SIZE = 512
class PortraitWorker(QThread):
    '''Worker thread for portrait matting.'''
    progress = Signal(float)
    finished = Signal(object, str)
    def __init__(self, image = None, parent = None):
        super().__init__(parent)
        self.image = image
        self._cancelled = False
    def run(self):
        try:
            if self._cancelled:
                self.finished.emit(None, 'Cancelled')
                return
            processor = PortraitMode()
            self.progress.emit(0.1)
            matte = processor._process_sync(self.image)
            if self._cancelled:
                self.finished.emit(None, 'Cancelled')
                return
            self.progress.emit(1.0)
            self.finished.emit(matte, '')
        except Exception as exc:
            self.finished.emit(None, str(exc))

    def cancel(self):
        self._cancelled = True
class PortraitMode(QObject):
    '''
    Portrait matting using MODNet.
    Specialized for portraits with fine hair detail preservation.
    Uses MODNet ONNX model for fast, high-quality matting.
    '''
    processing_started = Signal()
    processing_progress = Signal(float)
    processing_finished = Signal(object)
    processing_error = Signal(str)
    model_loading = Signal(float)
    def __init__(self, parent = None):
        super().__init__(parent)
        self._worker = None
    def is_model_loaded(self):
        '''Check if MODNet model is loaded.'''
        manager = get_model_manager()
        return manager.get_modnet_session() is not None
    def is_model_downloaded(self):
        '''Check if MODNet model is downloaded.'''
        manager = get_model_manager()
        return manager.is_modnet_downloaded()
    def download_model(self, progress_callback = None):
        '''
        Download the MODNet model.
        Args:
            progress_callback: Optional callback for progress updates
        Returns:
            True if download successful
        '''
        manager = get_model_manager()
        return manager.download_modnet_model(progress_callback)
    def load_model(self):
        '''
        Load the MODNet model.
        Returns:
            True if loaded successfully
        '''
        manager = get_model_manager()
        try:
            manager.model_loading.connect(self._on_model_loading)
        except Exception:
            pass
        return manager.load_modnet_model()

    def _on_model_loading(self, name = None, progress = None):
        '''Handle model loading progress.'''
        if name == 'modnet':
            self.model_loading.emit(progress)
            return None
    def process(self, image = None, async_mode = None):
        '''
        Generate portrait matte.
        Args:
            image: PIL Image to process
            async_mode: If True, process in background thread
        Returns:
            If async_mode=False: Matte as PIL Image (grayscale)
            If async_mode=True: None (results via signals)
        '''
        self.cancel()
        if async_mode:
            self._worker = PortraitWorker(image, self)
            self._worker.progress.connect(self.processing_progress.emit)
            self._worker.finished.connect(self._on_worker_finished)
            self.processing_started.emit()
            self._worker.start()
            return None
        return self._process_sync(image)
    def _process_sync(self, image = None):
        '''Synchronous portrait matting.'''
        manager = get_model_manager()
        session = manager.get_modnet_session()
        if session is None:
            if not self.load_model():
                raise RuntimeError('Failed to load MODNet model')
            session = manager.get_modnet_session()
        original_size = image.size
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        (w, h) = img_rgb.size
        scale = MODNET_INPUT_SIZE / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_resized = img_rgb.resize((new_w, new_h), Image.BILINEAR)
        padded = Image.new('RGB', (MODNET_INPUT_SIZE, MODNET_INPUT_SIZE), (124, 116, 104))
        pad_x = (MODNET_INPUT_SIZE - new_w) // 2
        pad_y = (MODNET_INPUT_SIZE - new_h) // 2
        padded.paste(img_resized, (pad_x, pad_y))
        img_np = np.array(padded, np.float32)
        img_np = img_np / 255
        mean = np.array([
            0.485,
            0.456,
            0.406], np.float32)
        std = np.array([
            0.229,
            0.224,
            0.225], np.float32)
        img_np = (img_np - mean) / std
        img_np = img_np.transpose(2, 0, 1)
        img_np = np.expand_dims(img_np, 0)
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        try:
            result = session.run([
                output_name], {
                input_name: img_np })[0]
        except Exception as exc:
            if manager.use_gpu and ModelManager.is_gpu_runtime_error(exc):
                logger.warning('GPU portrait inference failed; retrying on CPU: %s', exc)
                manager._mark_gpu_runtime_failed(exc)
                if not manager.load_modnet_model():
                    raise
                session = manager.get_modnet_session()
                input_name = session.get_inputs()[0].name
                output_name = session.get_outputs()[0].name
                result = session.run([
                    output_name], {
                    input_name: img_np })[0]
            else:
                raise
        matte = result[(0, 0)]
        matte = np.clip(matte, 0, 1)
        matte_uint8 = (matte * 255).astype(np.uint8)
        matte_pil = Image.fromarray(matte_uint8, 'L')
        matte_cropped = matte_pil.crop((pad_x, pad_y, pad_x + new_w, pad_y + new_h))
        matte_pil = matte_cropped.resize(original_size, Image.BILINEAR)
        return matte_pil
    def _on_worker_finished(self, matte = None, error = None):
        '''Handle worker completion.'''
        sender = self.sender()
        if sender is not self._worker:
            if sender is not None:
                sender.deleteLater()
            return None
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        if matte is None:
            self.processing_error.emit(error or 'Unknown error')
            return None
        self.processing_finished.emit(matte)
    def apply_matte(self, image = None, matte = None):
        '''
        Apply matte to image, making background transparent.
        Args:
            image: Original PIL Image
            matte: Grayscale matte image
        Returns:
            RGBA PIL Image with matte applied
        '''
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        if matte.mode != 'L':
            matte = matte.convert('L')
        if matte.size != image.size:
            matte = matte.resize(image.size, Image.LANCZOS)
        result = image.copy()
        result.putalpha(matte)
        return result
    def refine_matte(self, matte: Image.Image = None, sharpen: float = 0, expand: int = 0, feather: int = 0):
        '''
        Refine the matte with edge adjustments.
        Args:
            matte: Grayscale matte image
            sharpen: Edge sharpness (-1.0 to 1.0)
            expand: Pixels to expand (positive) or contract (negative)
            feather: Edge feather amount in pixels
        Returns:
            Refined matte image
        '''
        import cv2
        matte_np = np.array(matte)
        if expand != 0:
            kernel_size = abs(expand) * 2 + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            if expand > 0:
                matte_np = cv2.dilate(matte_np, kernel, 1)
            else:
                matte_np = cv2.erode(matte_np, kernel, 1)
        if feather > 0:
            matte_np = cv2.GaussianBlur(matte_np, (feather * 2 + 1, feather * 2 + 1), 0)
        if sharpen != 0:
            blurred = cv2.GaussianBlur(matte_np, (0, 0), 3)
            sharpened = cv2.addWeighted(matte_np, 1 + sharpen, blurred, -sharpen, 0)
            matte_np = np.clip(sharpened, 0, 255).astype(np.uint8)
        return Image.fromarray(matte_np, 'L')
    def cancel(self, blocking = None):
        '''Cancel current processing.
        Args:
            blocking: If True, wait for worker to finish. If False, just
                      signal cancellation and return immediately (used by closeEvent).
        '''
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            if blocking:
                if not self._worker.wait(5000):
                    logger.warning('Portrait worker did not finish within timeout, forcing termination')
                    self._worker.terminate()
                    self._worker.wait(1000)
                self._worker = None
                return None
    def is_processing(self):
        '''Check if currently processing.'''
        return self._worker is not None and self._worker.isRunning()
