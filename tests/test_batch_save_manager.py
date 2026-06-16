import tempfile
import unittest
from pathlib import Path

from PIL import Image

from src.processing.batch_queue import QueueItem
from src.processing.batch_save_manager import BatchSaveManager


class BatchSaveManagerTest(unittest.TestCase):
    def test_save_item_writes_unique_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = BatchSaveManager(tmp, format='png', naming='{original}_nobg')
            item = QueueItem(file_path=str(Path(tmp) / 'sample.jpg'))
            item.result_image = Image.new('RGBA', (4, 4), (255, 0, 0, 128))

            first = Path(manager.save_item(item))
            second = Path(manager.save_item(item))

            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertNotEqual(first, second)
            self.assertEqual(first.suffix.lower(), '.png')
            self.assertEqual(manager.saved_count, 2)


if __name__ == '__main__':
    unittest.main()
