'''
Processing Cache for QuestCut-AI
=============================
Caches processed masks to avoid redundant AI processing.
'''
import logging
import threading
import hashlib
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from PIL import Image
logger = logging.getLogger(__name__)
@dataclass
class CacheEntry:
    mask: Optional[np.ndarray] = None
    timestamp: Optional[datetime] = None
    image_hash: Optional[str] = None
    model_name: Optional[str] = None
    edge_settings: Optional[Dict[str, Any]] = field(default_factory=dict)
    refined_mask: Optional[np.ndarray] = None
class ProcessingCache:
    '''
    Caches AI-generated masks to optimize performance.
    The cache allows:
    - Changing background without reprocessing
    - Changing shadow without reprocessing
    - Changing position/transform without reprocessing
    - Only reprocess when: image changes, model changes, or edge settings need reapplication
    Brush edits are stored as refined_mask on top of the base mask.
    '''
    def __init__(self, max_entries = None):
        '''
        Initialize the cache.
        Args:
            max_entries: Maximum number of cached entries (LRU eviction)
        '''
        self._lock = threading.Lock()
        self._cache = { }
        self._max_entries = max_entries
        self._access_order = []
        self._current_image_hash = None
        self._current_entry = None
    @staticmethod
    def compute_image_hash(image=None):
        """Compute a hash for an image to detect changes."""
        thumb = image.copy()
        thumb.thumbnail((16, 16), Image.NEAREST)
        if thumb.mode != 'RGB':
            thumb = thumb.convert('RGB')
        h = hashlib.md5()
        h.update(f'{image.width}x{image.height}_{image.mode}_'.encode())
        h.update(thumb.tobytes())
        return h.hexdigest()
    def get_cached_mask(self, image = None, model_name = None):
        '''
        Get cached mask if available.
        Args:
            image: The source image
            model_name: The model used for processing
        Returns:
            Cached mask array or None if not cached
        '''
        image_hash = self.compute_image_hash(image)
        cache_key = f'''{image_hash}_{model_name}'''
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._access_order.append(cache_key)
                self._current_image_hash = image_hash
                self._current_entry = entry
                logger.debug(f'''Cache hit for {cache_key}''')
                return entry.mask
        logger.debug(f'''Cache miss for {cache_key}''')
        return None
    def store_mask(self, image=None, mask=None, model_name=None, edge_settings=None):
        '''
        Store a processed mask in the cache.
        Args:
            image: The source image
            mask: The generated mask
            model_name: The model used
            edge_settings: Edge refinement settings used
        '''
        image_hash = self.compute_image_hash(image)
        cache_key = f'''{image_hash}_{model_name}'''
        if edge_settings is None:
            edge_settings = {}
        entry = CacheEntry(
            mask=mask.copy(),
            timestamp=datetime.now(),
            image_hash=image_hash,
            model_name=model_name,
            edge_settings=edge_settings
        )
        with self._lock:
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            if cache_key not in self._cache and len(self._cache) >= self._max_entries:
                self._evict_oldest()
            if cache_key not in self._cache:
                self._cache[cache_key] = entry
                self._access_order.append(cache_key)
                self._current_image_hash = image_hash
                self._current_entry = entry
        logger.debug(f'''Stored mask in cache: {cache_key}''')
    def update_refined_mask(self, refined_mask = None):
        '''
        Update the current entry with a refined (brush-edited) mask.
        Args:
            refined_mask: The mask after brush edits
        '''
        with self._lock:
            if self._current_entry is not None:
                self._current_entry.refined_mask = refined_mask.copy()
                logger.debug('Updated refined mask in cache')
    def get_current_mask(self):
        '''Get the current working mask.'''
        with self._lock:
            if self._current_entry is not None:
                if self._current_entry.refined_mask is not None:
                    return self._current_entry.refined_mask
                return self._current_entry.mask
            return None
    def get_base_mask(self):
        '''Get the base (un-refined) mask for the current entry.'''
        with self._lock:
            if self._current_entry is not None:
                return self._current_entry.mask
            return None
    def clear_refinements(self):
        '''Clear brush refinements, reverting to base mask.'''
        with self._lock:
            if self._current_entry is not None:
                self._current_entry.refined_mask = None
                logger.debug('Cleared mask refinements')
    def invalidate(self, image = None):
        '''
        Invalidate cache entries.
        Args:
            image: If provided, only invalidate entries for this image.
                   If None, clear entire cache.
        '''
        with self._lock:
            if image is None:
                self._cache.clear()
                self._access_order.clear()
                self._current_entry = None
                self._current_image_hash = None
                logger.debug('Cleared entire cache')
            else:
                image_hash = self.compute_image_hash(image)
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(image_hash)]
                for key in keys_to_remove:
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
                if self._current_image_hash == image_hash:
                    self._current_entry = None
                    self._current_image_hash = None
                logger.debug(f'''Invalidated {len(keys_to_remove)} cache entries''')
    def _evict_oldest(self):
        '''Evict the least recently used entry.'''
        if self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
                logger.debug(f'''Evicted cache entry: {oldest_key}''')
                return None
    def is_cached(self, image = None, model_name = None):
        '''Check if a mask is cached for the given image and model.'''
        image_hash = self.compute_image_hash(image)
        cache_key = f'''{image_hash}_{model_name}'''
        with self._lock:
            return cache_key in self._cache
    def get_stats(self):
        '''Get cache statistics.'''
        with self._lock:
            return {
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'current_image': self._current_image_hash[:8] if self._current_image_hash else None,
                'has_refinements': self._current_entry.refined_mask is not None if self._current_entry else False
            }
_processing_cache: Optional[ProcessingCache] = None
_cache_init_lock = threading.Lock()
def get_processing_cache():
    '''Get the global processing cache instance.'''
    global _processing_cache
    if _processing_cache is None:
        with _cache_init_lock:
            if _processing_cache is None:
                _processing_cache = ProcessingCache()
    return _processing_cache
