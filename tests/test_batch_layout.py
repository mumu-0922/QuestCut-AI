import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy

from src.processing.batch_queue import QueueItem, QueueProgress
from src.ui.batch_config_dialog import BatchConfigDialog
from src.ui.batch_queue_panel import BatchItemWidget
from src.ui.batch_summary_dialog import BatchSummaryDialog


class BatchLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_batch_config_long_names_are_compacted_with_full_tooltip(self):
        long_name = 'jimeng-2026-03-04-3269-3d皮克斯风格-满仔-' * 6 + '.png'
        files = [str(Path('/tmp') / long_name), str(Path('/tmp') / ('第二张-' + long_name))]
        dialog = BatchConfigDialog(files, 'birefnet')
        try:
            self.assertTrue(dialog.names_label.wordWrap())
            self.assertEqual(dialog.names_label.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
            self.assertIn('…', dialog.names_label.text())
            self.assertIn(long_name, dialog.names_label.toolTip())

            dialog.naming_input.setText('{original}_' + ('超长导出命名模板-' * 8))
            self.assertTrue(dialog.preview_label.wordWrap())
            self.assertEqual(dialog.preview_label.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
            self.assertIn('…', dialog.preview_label.text())
            self.assertIn('超长导出命名模板', dialog.preview_label.toolTip())
        finally:
            dialog.close()

    def test_batch_summary_long_failure_and_output_path_are_compacted(self):
        class FakeImage:
            def __init__(self):
                self.file_path = str(Path('/tmp') / ('批量失败图片-' * 16 + '.png'))
                self.error_message = 'CUBLAS_STATUS_NOT_INITIALIZED ' * 14
                self.status = 'error'

            @property
            def has_error(self):
                return True

            @property
            def filename(self):
                return Path(self.file_path).name

        progress = QueueProgress(completed=0, total=1, failed=1, skipped=0)
        output_dir = str(Path('/tmp') / ('very-long-output-folder-name-' * 10))
        image = FakeImage()
        full_error = f'{image.filename}: {image.error_message}'
        dialog = BatchSummaryDialog(
            progress=progress,
            batch_images=[image],
            output_dir=output_dir,
            elapsed_time=3,
            save_stats={'saved_count': 0, 'total_mb': 0},
        )
        try:
            labels = dialog.findChildren(QLabel)
            failure_label = next(label for label in labels if label.toolTip() == full_error)
            dir_label = next(label for label in labels if label.toolTip() == output_dir)

            for label in (failure_label, dir_label):
                self.assertTrue(label.wordWrap())
                self.assertEqual(label.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
                self.assertIn('…', label.text())
                self.assertLess(len(label.text()), len(label.toolTip()))
        finally:
            dialog.close()

    def test_batch_item_widget_long_filename_is_compacted(self):
        long_name = '超长图片文件名-' * 12 + '.png'
        item = QueueItem(file_path=str(Path('/tmp') / long_name))
        widget = BatchItemWidget(item, defer_thumbnail=True)
        try:
            self.assertEqual(widget.status_label.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
            self.assertIn('…', widget.status_label.text())
            self.assertEqual(widget.status_label.toolTip(), long_name)
            self.assertLessEqual(widget.status_label.maximumWidth(), 72)
        finally:
            widget.close()


if __name__ == '__main__':
    unittest.main()
