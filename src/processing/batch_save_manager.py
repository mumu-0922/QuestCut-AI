'''
Batch Save Manager for QuestCut-AI
===============================
Handles auto-saving batch results immediately after processing
to release memory and prevent OOM issues.
'''
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from .batch_queue import QueueItem, ItemStatus
logger = logging.getLogger(__name__)
class BatchSaveManager:
    '''
    Manages saving batch processing results.
    Features:
    - Auto-save immediately after processing each item
    - Memory release after save
    - Configurable output format and naming
    - Error handling with retry support
    '''
    def __init__(self, output_dir: str = None, format: str = 'png', naming: str = '{original}_nobg', quality: int = 90):
        """
        Initialize the save manager.
        Args:
            output_dir: Directory to save processed images
            format: Output format ('png', 'jpg', 'webp')
            naming: Naming template with {original} placeholder
            quality: JPEG/WebP quality (1-100)
        """
        self.output_dir = Path(output_dir)
        self.format = format.lower()
        self.naming = naming
        self.quality = quality
        self.saved_count = 0
        self.failed_count = 0
        self.total_bytes_saved = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)
    def _get_output_path(self, item = None):
        '''Generate the output path for an item.'''
        original_name = Path(item.file_path).stem
        new_name = self.naming.replace('{original}', original_name)
        ext_map = {
            'png': '.png',
            'jpg': '.jpg',
            'jpeg': '.jpg',
            'webp': '.webp' }
        ext = ext_map.get(self.format, '.png')
        return self.output_dir / f'''{new_name}{ext}'''
    def save_item(self, item = None):
        '''
        Save a processed item to disk.
        Args:
            item: The queue item with result_image to save
        Returns:
            The actual saved file path (str) if successful, None otherwise.
            The path may include a conflict suffix (e.g. _1, _2) if the
            original filename already existed on disk.
        '''
        if item is None or item.result_image is None:
            logger.warning('No result image to save')
            return None
        output_path = self._get_output_path(item)
        if output_path.exists():
            counter = 1
            stem = output_path.stem
            while output_path.exists():
                output_path = output_path.parent / f'''{stem}_{counter}{output_path.suffix}'''
                counter += 1
        img = item.result_image
        if self.format in ('jpg', 'jpeg'):
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=self.quality, optimize=True)
        elif self.format == 'webp':
            if img.mode not in ('RGBA', 'RGB'):
                img = img.convert('RGBA')
            img.save(output_path, 'WEBP', quality=self.quality)
        else:
            if img.mode not in ('RGBA', 'RGB'):
                img = img.convert('RGBA')
            img.save(output_path, 'PNG', optimize=True)
        self.saved_count += 1
        self.total_bytes_saved += output_path.stat().st_size
        logger.info(f'''Saved: {output_path.name}''')
        return str(output_path)
    def get_statistics(self):
        '''Get save statistics.'''
        return {
            'saved_count': self.saved_count,
            'failed_count': self.failed_count,
            'total_bytes': self.total_bytes_saved,
            'total_mb': self.total_bytes_saved / 1048576,
            'output_dir': str(self.output_dir) }
    def reset(self):
        '''Reset statistics.'''
        self.saved_count = 0
        self.failed_count = 0
        self.total_bytes_saved = 0
class BatchSaveConfig:
    '''Configuration for batch saving.'''
    def __init__(self, format: str = 'png', quality: int = 90, naming_template: str = '{original}_nobg', create_subfolder: bool = False, subfolder_name: str = 'processed'):
        self.format = format
        self.quality = quality
        self.naming_template = naming_template
        self.create_subfolder = create_subfolder
        self.subfolder_name = subfolder_name
    def create_manager(self, output_dir = None):
        '''Create a BatchSaveManager with this configuration.'''
        if self.create_subfolder:
            output_dir = str(Path(output_dir) / self.subfolder_name)
        return BatchSaveManager(output_dir=output_dir, format=self.format, naming=self.naming_template, quality=self.quality)
