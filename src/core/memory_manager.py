"""
Memory Manager for QuestCut-AI
==========================
Manages memory during bulk processing to prevent OOM errors.
"""
import gc
import logging
import threading
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import psutil
from PIL import Image
logger = logging.getLogger(__name__)
@dataclass
class MemoryStats:
    process_memory_mb: float = 0
    available_memory_mb: float = 0
    total_memory_mb: float = 0
    memory_percent: float = 0
    is_critical: bool = False
class MemoryManager:
    DEFAULT_CRITICAL_THRESHOLD = 0.9
    DEFAULT_WARNING_THRESHOLD = 0.75
    DEFAULT_CLEANUP_THRESHOLD = 0.7
    BASE_MEMORY_PER_IMAGE = 50
    MEMORY_PER_MEGAPIXEL = 12
    def __init__(self):
        self._process = psutil.Process()
        self._cleanup_callbacks = []
        self._callbacks_lock = threading.Lock()
        self._high_memory_mode = False
        self.CRITICAL_THRESHOLD = self.DEFAULT_CRITICAL_THRESHOLD
        self.WARNING_THRESHOLD = self.DEFAULT_WARNING_THRESHOLD
        self.CLEANUP_THRESHOLD = self.DEFAULT_CLEANUP_THRESHOLD
    def get_memory_stats(self):
        mem = psutil.virtual_memory()
        process_mem = self._process.memory_info()
        return MemoryStats(
            process_memory_mb=process_mem.rss / 1048576,
            available_memory_mb=mem.available / 1048576,
            total_memory_mb=mem.total / 1048576,
            memory_percent=mem.percent,
            is_critical=mem.percent > self.CRITICAL_THRESHOLD * 100)
    def estimate_image_memory(self, width, height):
        megapixels = width * height / 1000000
        return self.BASE_MEMORY_PER_IMAGE + megapixels * self.MEMORY_PER_MEGAPIXEL
    def calculate_max_concurrent(self, images, safety_factor=0.75):
        stats = self.get_memory_stats()
        available_mb = stats.available_memory_mb * safety_factor
        if not images:
            return 1
        total_memory = 0
        for img in images:
            if isinstance(img, Image.Image):
                width, height = img.size
            elif isinstance(img, tuple) and len(img) == 2:
                width, height = img
            else:
                width, height = (2000, 2000)
            total_memory += self.estimate_image_memory(width, height)
        avg_memory = total_memory / len(images)
        max_concurrent = max(1, int(available_mb / avg_memory))
        return min(max_concurrent, 4)
    def should_cleanup(self):
        stats = self.get_memory_stats()
        return stats.memory_percent > self.CLEANUP_THRESHOLD * 100
    def should_pause_processing(self):
        stats = self.get_memory_stats()
        return stats.is_critical
    def cleanup(self, aggressive=False):
        logger.debug("Starting memory cleanup...")
        with self._callbacks_lock:
            for cb in list(self._cleanup_callbacks):
                try:
                    cb(aggressive)
                except Exception:
                    pass
        gc.collect()
    def register_cleanup_callback(self, callback):
        with self._callbacks_lock:
            self._cleanup_callbacks.append(callback)
    def unregister_cleanup_callback(self, callback):
        with self._callbacks_lock:
            if callback in self._cleanup_callbacks:
                self._cleanup_callbacks.remove(callback)
    @contextmanager
    def processing_context(self, image_info=None):
        if self.should_pause_processing():
            logger.warning("Memory critical, performing cleanup before processing")
            self.cleanup(aggressive=True)
        try:
            yield
        finally:
            if self.should_cleanup():
                self.cleanup()
    def release_image(self, image):
        if image is not None:
            image.close()
    def release_images(self, images):
        for img in images:
            self.release_image(img)
        images.clear()
    def enable_high_memory_mode(self):
        self._high_memory_mode = True
        self.CLEANUP_THRESHOLD = 0.6
        logger.info("High memory mode enabled")
    def disable_high_memory_mode(self):
        self._high_memory_mode = False
        self.CLEANUP_THRESHOLD = self.DEFAULT_CLEANUP_THRESHOLD
        logger.info("High memory mode disabled")
    def log_memory_status(self):
        stats = self.get_memory_stats()
        level = logging.WARNING if stats.is_critical else (
            logging.INFO if stats.memory_percent > self.WARNING_THRESHOLD * 100 else logging.DEBUG)
        logger.log(level, f"Memory: {stats.process_memory_mb:.0f}MB process, "
                   f"{stats.available_memory_mb:.0f}MB available ({stats.memory_percent:.1f}% used)")
_memory_manager: Optional[MemoryManager] = None
_memory_manager_lock = threading.Lock()
def get_memory_manager():
    global _memory_manager
    if _memory_manager is None:
        with _memory_manager_lock:
            if _memory_manager is None:
                _memory_manager = MemoryManager()
    return _memory_manager
def cleanup_memory(aggressive=False):
    get_memory_manager().cleanup(aggressive)
def get_memory_stats():
    return get_memory_manager().get_memory_stats()
def processing_context(image_info=None):
    return get_memory_manager().processing_context(image_info)
