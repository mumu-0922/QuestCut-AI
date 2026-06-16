'''
Batch Processing Queue for QuestCut-AI
===================================
Queue management with pause/resume/skip controls.
'''
import logging
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from PySide6.QtCore import QObject, Signal, QThread, QMutex, QWaitCondition
from PIL import Image
from ..core.memory_manager import get_memory_manager, cleanup_memory
logger = logging.getLogger(__name__)
class ItemStatus(Enum):
    '''Status of a queue item.'''
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'
class QueueStatus(Enum):
    '''Status of the queue.'''
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    CANCELLED = 'cancelled'
@dataclass
class QueueItem:
    file_path: str = ''
    status: ItemStatus = ItemStatus.PENDING
    result_image: Optional[Any] = None
    result_mask: Optional[Any] = None
    error_message: str = ''
    progress: float = 0.0
    original_name: str = ''


@dataclass
class QueueProgress:
    completed: int = 0
    total: int = 0
    failed: int = 0
    skipped: int = 0
    saved: int = 0
    current_item: str = ''
    percentage: float = 0.0
class BatchWorker(QThread):
    '''Worker thread for batch processing with auto-save and memory optimization.'''
    item_started = Signal(object)
    item_progress = Signal(object, float)
    item_completed = Signal(object)
    item_failed = Signal(object, str)
    item_saved = Signal(object)
    queue_progress = Signal(object)
    def __init__(self, items = None, process_func = None, save_func = None, auto_save = None, chunk_size = None, parent = None):
        '''
        Initialize the batch worker.
        Args:
            items: List of items to process
            process_func: Function that takes file path and returns (image, mask)
            save_func: Optional function to save item results
            auto_save: If True, save and release memory immediately after processing
            chunk_size: Number of items to process before aggressive GC
        '''
        super().__init__(parent)
        self.items = items
        self.process_func = process_func
        self.save_func = save_func
        self.auto_save = auto_save
        self.chunk_size = chunk_size
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()
        self._paused = False
        self._cancelled = False
        self._skip_current = False
        self._completed = 0
        self._failed = 0
        self._skipped = 0
        self._saved = 0
    def run(self):
        '''Process all items in the queue with parallel execution and memory optimization.'''
        import gc
        from concurrent.futures import ThreadPoolExecutor, Future
        memory_manager = get_memory_manager()
        memory_manager.enable_high_memory_mode()
        max_workers = self._calculate_workers()
        logger.info(f'''Batch processing with {max_workers} parallel worker(s)''')
        try:
            if max_workers <= 1:
                self._run_sequential(memory_manager, gc)
            else:
                self._run_parallel(memory_manager, gc, max_workers)
        finally:
            memory_manager.disable_high_memory_mode()
            memory_manager.cleanup(True)
            gc.collect()
            return None
            memory_manager.disable_high_memory_mode()
            memory_manager.cleanup(True)
            gc.collect()
            return None
            memory_manager.disable_high_memory_mode()
            memory_manager.cleanup(True)
            gc.collect()
    def _calculate_workers(self):
        '''Calculate optimal number of parallel workers based on available memory.'''
        return 1

    def _emit_progress(self, current_item=''):
        total = len(self.items)
        completed = sum(1 for item in self.items if item.status == ItemStatus.COMPLETED)
        failed = sum(1 for item in self.items if item.status == ItemStatus.FAILED)
        skipped = sum(1 for item in self.items if item.status == ItemStatus.SKIPPED)
        saved = self._saved
        done = completed + failed + skipped
        progress = QueueProgress(
            completed=completed,
            total=total,
            failed=failed,
            skipped=skipped,
            saved=saved,
            current_item=current_item,
            percentage=(done / total * 100) if total else 0.0,
        )
        self.queue_progress.emit(progress)

    def _run_sequential(self, memory_manager=None, gc=None):
        for item in self.items:
            if self._cancelled:
                item.status = ItemStatus.SKIPPED
                self._skipped += 1
                continue
            while self._paused and not self._cancelled:
                self._pause_condition.wait(self._mutex, 250)
            if self._cancelled:
                item.status = ItemStatus.SKIPPED
                self._skipped += 1
                continue
            if self._skip_current:
                self._skip_current = False
                item.status = ItemStatus.SKIPPED
                self._skipped += 1
                self._emit_progress(item.original_name or item.file_path)
                continue
            try:
                item.status = ItemStatus.PROCESSING
                self.item_started.emit(item)
                self._emit_progress(item.original_name or item.file_path)
                result_image, result_mask = self._process_single(item)
                if result_image is None:
                    raise RuntimeError('Processing returned no result')
                item.result_image = result_image
                item.result_mask = result_mask
                if self.auto_save and self.save_func:
                    saved_path = self.save_func(item)
                    if saved_path:
                        item.saved_path = saved_path
                        self._saved += 1
                        self.item_saved.emit(item)
                    else:
                        raise RuntimeError('Auto-save failed')
                item.status = ItemStatus.COMPLETED
                self._completed += 1
                self.item_completed.emit(item)
            except Exception as exc:
                item.status = ItemStatus.FAILED
                item.error_message = str(exc)
                self._failed += 1
                self.item_failed.emit(item, str(exc))
            finally:
                self._emit_progress(item.original_name or item.file_path)
                if gc is not None and (self._completed + self._failed + self._skipped) % max(1, self.chunk_size or 1) == 0:
                    try:
                        cleanup_memory()
                        gc.collect()
                    except Exception:
                        pass

    def _run_parallel(self, memory_manager=None, gc=None, max_workers=1):
        # AI inference sessions are usually not thread-safe; keep deterministic sequential processing.
        self._run_sequential(memory_manager, gc)

    def _process_single(self, item=None):
        """Process a single item (called from thread pool)."""
        return self.process_func(item.file_path)


class BatchQueue(QObject):
    """Manages a queue of items for batch processing with pause/resume/skip controls."""

    queue_started = Signal()
    item_started = Signal(object)
    item_failed = Signal(object, str)
    item_saved = Signal(object)
    queue_progress = Signal(object)
    progress_updated = Signal(object)
    item_completed = Signal(object)
    queue_finished = Signal(object)
    queue_paused = Signal()
    queue_resumed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._status = QueueStatus.IDLE
        self._worker = None
        self._mutex = QMutex()

    def add_items(self, items):
        """Add items to the queue."""
        for item in items:
            self._items.append(item)

    def add_files(self, files):
        """Add file paths to the queue."""
        for file_path in files or []:
            path = Path(file_path)
            self._items.append(QueueItem(file_path=str(path), original_name=path.name))

    def remove_item(self, index):
        """Remove an item from the queue."""
        if 0 <= index < len(self._items):
            del self._items[index]

    def clear(self):
        """Clear all items from the queue."""
        self._items.clear()
        self._status = QueueStatus.IDLE

    def start(self, process_func=None, save_func=None, auto_save=True, chunk_size=5):
        """Start processing the queue."""
        if not self._items:
            return
        self._status = QueueStatus.RUNNING
        self._worker = BatchWorker(
            items=self._items,
            process_func=process_func,
            save_func=save_func,
            auto_save=auto_save,
            chunk_size=chunk_size,
        )
        self._worker.queue_progress.connect(self.progress_updated.emit)
        self._worker.queue_progress.connect(self.queue_progress.emit)
        self._worker.item_started.connect(self.item_started.emit)
        self._worker.item_completed.connect(self.item_completed.emit)
        self._worker.item_failed.connect(self.item_failed.emit)
        self._worker.item_saved.connect(self.item_saved.emit)
        self._worker.finished.connect(self._on_worker_finished)
        self.queue_started.emit()
        self._worker.start()

    def pause(self):
        """Pause the queue."""
        if self._worker:
            self._worker._paused = True
            self._status = QueueStatus.PAUSED
            self.queue_paused.emit()

    def resume(self):
        """Resume the queue."""
        if self._worker:
            self._worker._paused = False
            self._worker._pause_condition.wakeAll()
            self._status = QueueStatus.RUNNING
            self.queue_resumed.emit()

    def cancel(self, blocking=False):
        """Cancel processing."""
        self._status = QueueStatus.CANCELLED
        if self._worker:
            self._worker._cancelled = True
            self._worker._paused = False
            self._worker._pause_condition.wakeAll()
            if blocking:
                self._worker.wait(5000)

    def skip_current(self):
        """Skip the current item."""
        if self._worker:
            self._worker._skip_current = True

    def _on_worker_finished(self):
        """Handle worker completion."""
        progress = QueueProgress(
            completed=sum(1 for item in self._items if item.status == ItemStatus.COMPLETED),
            total=len(self._items),
            failed=sum(1 for item in self._items if item.status == ItemStatus.FAILED),
            skipped=sum(1 for item in self._items if item.status == ItemStatus.SKIPPED),
            saved=sum(1 for item in self._items if getattr(item, 'saved_path', '')),
        )
        self._status = QueueStatus.IDLE
        self._worker = None
        self.queue_finished.emit(progress)

    def release_completed_results(self):
        """Release processed image references after auto-save."""
        for item in self._items:
            if getattr(item, 'saved_path', ''):
                item.result_image = None
                item.result_mask = None

    @property
    def status(self):
        return self._status

    @property
    def item_count(self):
        return len(self._items)

    def get_items(self):
        return list(self._items)
