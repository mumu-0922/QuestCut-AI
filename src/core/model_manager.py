"""
Model Manager for QuestCut-AI
==========================
Handles loading, caching, and management of AI models.
"""
import os
import sys
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal, QThread
from .gpu_utils import detect_gpu, get_device, get_onnx_providers, clear_gpu_memory, GPUInfo, GPUBackend
from ..utils.constants import MODEL_CONFIG
logger = logging.getLogger(__name__)
class ModelType(Enum):
    REMBG = "rembg"
    MODNET = "modnet"
@dataclass
class ModelStatus:
    name: str = ""
    loaded: bool = False
    loading: bool = False
    error: str = ""
class DownloadWorker(QThread):
    progress = Signal(float)
    finished = Signal(bool, str)
    def __init__(self, url, dest_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest_path = dest_path
        self._cancelled = False
    def run(self):
        try:
            import urllib.request
            dest = Path(self.dest_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            def report(count, block_size, total_size):
                if self._cancelled:
                    raise Exception("Cancelled")
                if total_size > 0:
                    self.progress.emit(min(count * block_size / total_size, 1.0))
            urllib.request.urlretrieve(self.url, str(dest), report)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))
    def cancel(self):
        self._cancelled = True
class ModelManager(QObject):
    model_loading = Signal(str, float)
    model_loaded = Signal(str)
    model_error = Signal(str, str)
    gpu_status_changed = Signal(GPUInfo)
    gpu_runtime_state_changed = Signal()
    def __init__(self, models_dir=None, parent=None):
        super().__init__(parent)
        if models_dir is None:
            app_data = Path(os.environ.get("APPDATA", Path.home() / ".questcut"))
            self.models_dir = app_data / "QuestCut-AI" / "models"
        else:
            self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._bundled_models_dirs = self._discover_model_dirs()
        self._model_lock = threading.RLock()
        self._rembg_session = None
        self._rembg_model_name = None
        self._modnet_session = None
        self._status = {}
        self._download_workers = {}
        self._gpu_info = None
        self._use_gpu = True
        self._gpu_runtime_failed = False
        self._last_gpu_error = ""
        self._detect_gpu()
    @property
    def rembg_model_name(self):
        return self._rembg_model_name
    def _detect_gpu(self):
        self._gpu_info = detect_gpu()
        logger.info(f"GPU detection: {self._gpu_info}")
        self.gpu_status_changed.emit(self._gpu_info)
    def _discover_model_dirs(self):
        """Return local model roots in priority order.

        The source tree keeps bundled ONNX files under models/.
        _decompiled_stdlib_backup/models is retained only as a legacy fallback.
        rembg will otherwise try to fetch missing models from the network,
        which leaves the UI stuck at 0% on offline machines.
        """
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(getattr(sys, "_MEIPASS", "")) / "models")
            candidates.append(Path(sys.executable).resolve().parent / "models")

        repo_root = Path(__file__).resolve().parents[2]
        candidates.extend([
            repo_root / "models",
            repo_root / "_decompiled_stdlib_backup" / "models",
            Path.cwd() / "models",
        ])

        discovered = []
        seen = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if resolved in seen or not resolved.is_dir():
                continue
            seen.add(resolved)
            discovered.append(resolved)
        return discovered

    def _model_filename(self, model_name):
        config = MODEL_CONFIG.get(model_name, {})
        rembg_model = config.get("rembg_model")
        if rembg_model:
            return f"{rembg_model}.onnx"
        return config.get("filename", f"{model_name}.onnx")

    def _find_model_file(self, model_name):
        """Find model file in bundled or downloaded models dir."""
        filename = self._model_filename(model_name)
        search_roots = [*self._bundled_models_dirs, self.models_dir]
        for root in search_roots:
            for subdir in ["rembg", "modnet", ""]:
                candidate = root / subdir / filename
                if candidate.exists():
                    return str(candidate)
        return None

    def _prepare_rembg_cache(self, model_name, model_path=None):
        """Point rembg/pooch at a local cache before creating a session."""
        if model_path:
            cache_dir = Path(model_path).resolve().parent
        else:
            cache_dir = self.models_dir / "rembg"
            cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["U2NET_HOME"] = str(cache_dir)
        return cache_dir
    @staticmethod
    def is_gpu_runtime_error(error):
        """Return True for ONNX Runtime provider failures that should fall back to CPU."""
        message = str(error or '').lower()
        needles = (
            'cuda',
            'cublas',
            'cudnn',
            'cufft',
            'curand',
            'cudaexecutionprovider',
            'dmlexecutionprovider',
            'directml',
            'gpu',
            'onnxruntimeerror',
        )
        return any(needle in message for needle in needles)

    def _providers_for_current_mode(self):
        if self._use_gpu and not self._gpu_runtime_failed:
            return get_onnx_providers()
        return ['CPUExecutionProvider']

    def _mark_gpu_runtime_failed(self, error):
        self._gpu_runtime_failed = True
        self._last_gpu_error = str(error or '')
        clear_gpu_memory()
        self._clear_all_models()
        logger.warning('GPU runtime failed; falling back to CPUExecutionProvider: %s', self._last_gpu_error)
        self.gpu_runtime_state_changed.emit()

    def _create_rembg_session(self, rembg_model, providers):
        from rembg import new_session
        return new_session(model_name=rembg_model, providers=providers)

    def _create_ort_session(self, model_path, providers):
        import onnxruntime as ort
        return ort.InferenceSession(model_path, providers=providers)

    def load_rembg_model(self, model_name):
        config = MODEL_CONFIG.get(model_name)
        if not config or "rembg_model" not in config:
            logger.warning(f"Unknown model: {model_name}")
            return False
        with self._model_lock:
            if self._rembg_session is not None and self._rembg_model_name == model_name:
                return True
            try:
                self.model_loading.emit(model_name, 0.05)
                rembg_model = config["rembg_model"]
                model_path = self._find_model_file(model_name)
                if model_path is None:
                    raise FileNotFoundError(
                        f"Model file not found for {model_name}: {self._model_filename(model_name)}"
                    )
                self._prepare_rembg_cache(model_name, model_path)
                self.model_loading.emit(model_name, 0.15)
                providers = self._providers_for_current_mode()
                try:
                    self._rembg_session = self._create_rembg_session(rembg_model, providers)
                except Exception as exc:
                    if (providers != ["CPUExecutionProvider"]
                            and self.is_gpu_runtime_error(exc)):
                        self._mark_gpu_runtime_failed(exc)
                        providers = ["CPUExecutionProvider"]
                        self.model_loading.emit(model_name, 0.18)
                        self._rembg_session = self._create_rembg_session(rembg_model, providers)
                    else:
                        raise
                self._rembg_model_name = model_name
                self.model_loading.emit(model_name, 0.25)
                self.model_loaded.emit(model_name)
                logger.info("Loaded rembg model: %s from %s with %s", model_name, model_path, providers)
                return True
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                self.model_error.emit(model_name, str(e))
                return False
    def get_rembg_session(self):
        with self._model_lock:
            return self._rembg_session

    def get_modnet_session(self):
        with self._model_lock:
            return self._modnet_session

    def is_modnet_downloaded(self):
        return self._find_model_file('modnet') is not None

    def download_modnet_model(self, progress_callback=None):
        config = MODEL_CONFIG.get('modnet', {})
        url = config.get('url')
        filename = config.get('filename', 'modnet.onnx')
        if not url:
            self.model_error.emit('modnet', 'MODNet URL is not configured')
            return False
        dest = self.models_dir / 'modnet' / filename
        if dest.exists():
            return True
        try:
            import urllib.request
            dest.parent.mkdir(parents=True, exist_ok=True)

            def report(count, block_size, total_size):
                if total_size > 0:
                    progress = min(count * block_size / total_size, 1.0)
                    self.model_loading.emit('modnet', progress)
                    if progress_callback:
                        progress_callback(progress)

            urllib.request.urlretrieve(url, str(dest), report)
            return True
        except Exception as e:
            logger.error(f'Failed to download MODNet model: {e}')
            self.model_error.emit('modnet', str(e))
            return False

    def load_modnet_model(self):
        with self._model_lock:
            if self._modnet_session is not None:
                return True
            try:
                self.model_loading.emit('modnet', 0.1)
                model_path = self._find_model_file('modnet')
                if model_path is None:
                    if not self.download_modnet_model():
                        return False
                    model_path = self._find_model_file('modnet')
                if model_path is None:
                    raise FileNotFoundError('modnet.onnx')
                providers = self._providers_for_current_mode()
                try:
                    self._modnet_session = self._create_ort_session(model_path, providers)
                except Exception as exc:
                    if (providers != ['CPUExecutionProvider']
                            and self.is_gpu_runtime_error(exc)):
                        self._mark_gpu_runtime_failed(exc)
                        providers = ['CPUExecutionProvider']
                        self.model_loading.emit('modnet', 0.18)
                        self._modnet_session = self._create_ort_session(model_path, providers)
                    else:
                        raise
                self.model_loaded.emit('modnet')
                logger.info('Loaded MODNet model: %s with %s', model_path, providers)
                return True
            except Exception as e:
                logger.error(f'Failed to load MODNet model: {e}')
                self.model_error.emit('modnet', str(e))
                return False
    @property
    def gpu_info(self):
        if self._gpu_info is None:
            self._detect_gpu()
        return self._gpu_info

    @property
    def gpu_requested(self):
        return self._use_gpu

    @property
    def gpu_runtime_failed(self):
        return self._gpu_runtime_failed

    @property
    def last_gpu_error(self):
        return self._last_gpu_error

    @property
    def gpu_available(self):
        info = self.gpu_info
        return bool(info and info.available)

    @property
    def use_gpu(self):
        return (self._use_gpu and not self._gpu_runtime_failed
                and self._gpu_info and self._gpu_info.available)

    @use_gpu.setter
    def use_gpu(self, value):
        self._use_gpu = bool(value)
        if value:
            self._gpu_runtime_failed = False
            self._last_gpu_error = ""
        self._clear_all_models()
        self.gpu_runtime_state_changed.emit()

    def retry_gpu(self):
        """Re-enable GPU after a runtime fallback and force sessions to reload."""
        self._use_gpu = True
        self._gpu_runtime_failed = False
        self._last_gpu_error = ""
        self._detect_gpu()
        self._clear_all_models()
        self.gpu_runtime_state_changed.emit()

    def device_status(self):
        """Return a small status dict for UI display."""
        info = self.gpu_info
        if not info or not info.available:
            return {
                "mode": "cpu",
                "title": "CPU mode (no GPU detected)",
                "detail": "Processing will use CPU.",
                "device": "CPU",
            }
        if self._gpu_runtime_failed:
            return {
                "mode": "fallback",
                "title": "GPU failed, using CPU",
                "detail": self._last_gpu_error,
                "device": info.device_name,
            }
        if self.use_gpu:
            return {
                "mode": "gpu",
                "title": "GPU active",
                "detail": info.device_name,
                "device": info.device_name,
            }
        return {
            "mode": "cpu",
            "title": "CPU mode",
            "detail": info.device_name,
            "device": "CPU",
        }

    @property
    def device(self):
        return get_device(self.use_gpu)
    def _clear_all_models(self):
        self._rembg_session = None
        self._rembg_model_name = None
        self._modnet_session = None
    def clear_models(self):
        with self._model_lock:
            self._clear_all_models()
_model_manager: Optional[ModelManager] = None
_model_manager_lock = threading.Lock()
def get_model_manager():
    global _model_manager
    if _model_manager is None:
        with _model_manager_lock:
            if _model_manager is None:
                _model_manager = ModelManager()
    return _model_manager
