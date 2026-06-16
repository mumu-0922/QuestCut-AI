import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.ui.batch_config_dialog import BatchConfig
from src.ui.batch_filmstrip import BatchImageState
from src.ui.elite_main_window import EliteMainWindow


class ExportControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QSettings('QuestCut', 'QuestCut-AI').setValue('has_shown_welcome', True)
        cls.app = QApplication.instance() or QApplication([])

    def test_quick_save_delegates_and_writes_unique_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sample.png'
            Image.new('RGBA', (4, 4), (1, 2, 3, 255)).save(source)
            window = EliteMainWindow()
            try:
                window._current_files = [str(source)]
                window._processed_image = Image.new('RGBA', (4, 4), (255, 0, 0, 128))

                first = Path(window._quick_save())
                second = Path(window._quick_save())

                self.assertTrue(first.exists())
                self.assertTrue(second.exists())
                self.assertNotEqual(first, second)
                self.assertEqual(first.name, 'sample_nobg.png')
                self.assertEqual(second.name, 'sample_nobg_1.png')
            finally:
                window.close()

    def test_save_current_batch_image_uses_controller_without_losing_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'batch-source.png'
            Image.new('RGBA', (4, 4), (10, 20, 30, 255)).save(source)
            output_dir = Path(tmp) / 'out'
            window = EliteMainWindow()
            try:
                image = Image.new('RGBA', (4, 4), (0, 255, 0, 128))
                mask = np.full((4, 4), 128, dtype=np.uint8)
                state = BatchImageState(id=1, file_path=str(source), status='processed')
                state.processed_image = image.copy()
                state.result_mask = Image.fromarray(mask, 'L')
                window._batch_mode = True
                window._batch_images = [state]
                window._batch_current_index = 0
                window._batch_output_dir = str(output_dir)
                window._batch_config = BatchConfig(output_dir=str(output_dir), export_format='png', naming_template='{original}_nobg')
                window._processed_image = image.copy()
                window._current_mask = mask.copy()

                saved = Path(window._save_current_batch_image())

                self.assertTrue(saved.exists())
                self.assertEqual(saved.parent, output_dir)
                self.assertEqual(state.status, 'saved')
                self.assertEqual(state.saved_path, str(saved))
                self.assertIsNotNone(state.result_mask)
            finally:
                window.close()


if __name__ == '__main__':
    unittest.main()
