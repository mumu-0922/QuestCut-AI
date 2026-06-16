import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.processing.batch_queue import QueueProgress
from src.ui.batch_config_dialog import BatchConfig
from src.ui.batch_filmstrip import BatchImageState
from src.ui.elite_main_window import EliteMainWindow


class BatchControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QSettings('QuestCut', 'QuestCut-AI').setValue('has_shown_welcome', True)
        cls.app = QApplication.instance() or QApplication([])

    def test_batch_finish_shows_summary_dialog_and_retry_resets_failed_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'failed.png'
            Image.new('RGBA', (4, 4), (10, 20, 30, 255)).save(source)
            window = EliteMainWindow()
            try:
                state = BatchImageState(id=1, file_path=str(source), status='error')
                state.error_message = 'boom'
                window._batch_mode = True
                window._batch_images = [state]
                window._batch_config = BatchConfig(output_dir=str(Path(tmp) / 'out'), model_key='birefnet')
                window._batch_output_dir = window._batch_config.output_dir
                progress = QueueProgress(completed=0, total=1, failed=1)

                with patch.object(window._batch_controller, '_start_queue') as start_queue:
                    window._on_batch_processing_finished(progress)
                    self.assertTrue(hasattr(window, '_batch_summary_dialog'))
                    self.assertFalse(window._batch_summary_dialog.isHidden())

                    window._batch_controller.retry_failed()

                    start_queue.assert_called_once()
                    self.assertEqual(state.status, 'pending')
                    self.assertEqual(state.error_message, '')
            finally:
                if hasattr(window, '_batch_summary_dialog'):
                    window._batch_summary_dialog.close()
                window.close()


if __name__ == '__main__':
    unittest.main()
