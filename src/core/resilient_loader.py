"""
Resilient Model Loader for QuestCut-AI
==================================
Timeout, retry logic, and error handling for model loading.
"""
import logging
import time
import threading
from typing import Optional, Callable, Any, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal
logger = logging.getLogger(__name__)
T = TypeVar("T")
class LoaderState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
@dataclass
class LoaderError:
    message: str = ""
    error_type: str = ""
    suggestion: str = ""
@dataclass
class LoaderResult(Generic[T]):
    success: bool = False
    result: Optional[T] = None
    error: Optional[LoaderError] = None
    duration: float = 0
    attempts: int = 0
class ResilientLoader(QObject):
    loading_started = Signal(str)
    loading_progress = Signal(str, float)
    loading_finished = Signal(str, bool)
    loading_error = Signal(str, str)
    DEFAULT_TIMEOUT = 60
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2
    DEFAULT_BACKOFF_FACTOR = 2
    def __init__(self, timeout=None, max_retries=None, retry_delay=None,
                 backoff_factor=None, parent=None):
        super().__init__(parent)
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY
        self.backoff_factor = backoff_factor or self.DEFAULT_BACKOFF_FACTOR
        self._state = LoaderState.IDLE
        self._cancelled = False
        self._lock = threading.Lock()
    @property
    def state(self):
        return self._state
    def cancel(self):
        with self._lock:
            self._cancelled = True
            self._state = LoaderState.CANCELLED
    def reset(self):
        with self._lock:
            self._cancelled = False
            self._state = LoaderState.IDLE
    def load_with_retry(self, operation_name, load_function, progress_callback=None):
        self.reset()
        self._state = LoaderState.LOADING
        self.loading_started.emit(operation_name)
        start_time = time.time()
        last_error = None
        for attempt in range(self.max_retries):
            if self._cancelled:
                return LoaderResult(success=False, error=LoaderError(
                    message="Cancelled", error_type="cancelled"),
                    duration=time.time() - start_time, attempts=attempt)
            try:
                self.loading_progress.emit(operation_name, attempt / self.max_retries)
                result = load_function()
                self._state = LoaderState.SUCCESS
                self.loading_finished.emit(operation_name, True)
                return LoaderResult(success=True, result=result,
                                    duration=time.time() - start_time,
                                    attempts=attempt + 1)
            except Exception as e:
                last_error = e
                logger.warning(f"Load attempt {attempt + 1}/{self.max_retries} "
                               f"for {operation_name} failed: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    time.sleep(delay)
        self._state = LoaderState.FAILED
        suggestion = self._get_error_suggestion(operation_name, last_error)
        err = LoaderError(message=str(last_error),
                          error_type=type(last_error).__name__,
                          suggestion=suggestion)
        self.loading_error.emit(operation_name, str(last_error))
        return LoaderResult(success=False, error=err,
                            duration=time.time() - start_time,
                            attempts=self.max_retries)
    def _get_error_suggestion(self, operation_name, error):
        error_str = str(error).lower()
        if any(x in error_str for x in ("connection", "network", "timeout", "url")):
            return "Check your internet connection."
        if "gpu" in error_str or "cuda" in error_str:
            return "Try disabling GPU acceleration in settings."
        error_type = type(error).__name__
        if error_type in ("ImportError", "ModuleNotFoundError"):
            return "Missing dependency. Try reinstalling requirements."
        return "Check your connection and try again."
    def cleanup(self):
        pass
class ModelLoadingManager:
    def __init__(self):
        self._loader = ResilientLoader()
        self._lock = threading.Lock()
        self._loading_models = set()
        self._active_loaders = {}
    def is_loading(self, model_name):
        with self._lock:
            return model_name in self._loading_models
    def load_model(self, model_name, load_function, timeout=None, max_retries=None):
        with self._lock:
            if model_name in self._loading_models:
                return None
            self._loading_models.add(model_name)
        try:
            loader = ResilientLoader(timeout=timeout, max_retries=max_retries)
            with self._lock:
                self._active_loaders[model_name] = loader
            return loader.load_with_retry(model_name, load_function)
        finally:
            with self._lock:
                self._active_loaders.pop(model_name, None)
                self._loading_models.discard(model_name)
    def cancel_loading(self, model_name):
        with self._lock:
            loader = self._active_loaders.get(model_name)
            if loader:
                loader.cancel()
_loading_manager: Optional[ModelLoadingManager] = None
_loading_manager_lock = threading.Lock()
def get_loading_manager():
    global _loading_manager
    if _loading_manager is None:
        with _loading_manager_lock:
            if _loading_manager is None:
                _loading_manager = ModelLoadingManager()
    return _loading_manager


def with_retry(max_attempts=3, delay=1.0):
    """Decorator that retries a function on failure."""
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator
