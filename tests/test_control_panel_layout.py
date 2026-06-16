import os
import unittest
import unittest.mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy

from src.ui.control_panel import ControlPanel
from src.ui.shortcuts_dialog import ShortcutsDialog


class ControlPanelLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_long_status_message_is_elided_and_does_not_widen_panel(self):
        panel = ControlPanel()
        try:
            message = '已加载 ' + ('jimeng-2026-03-04-3269-3d皮克斯风格-满仔-' * 8) + '.png'
            panel.set_status(message)

            self.assertTrue(panel.status_label.wordWrap())
            self.assertLessEqual(panel.status_label.maximumWidth(), 300)
            self.assertEqual(panel.status_label.sizePolicy().horizontalPolicy(), QSizePolicy.Ignored)
            self.assertIn('…', panel.status_label.text())
            self.assertEqual(panel.status_label.toolTip(), message)
            self.assertLess(len(panel.status_label.text()), len(message))
        finally:
            panel.close()

    def test_gpu_and_batch_labels_wrap_inside_control_panel(self):
        panel = ControlPanel()
        try:
            detail = 'CUDA fallback: ' + ('CUBLAS_STATUS_NOT_INITIALIZED ' * 10)
            panel.set_gpu_controls(
                requested=True,
                available=True,
                active=False,
                failed=True,
                status_text='GPU unavailable',
                detail_text=detail,
            )

            self.assertTrue(panel.gpu_status_label.wordWrap())
            self.assertLessEqual(panel.gpu_status_label.maximumWidth(), 300)
            self.assertIn('…', panel.gpu_status_label.text())
            self.assertIn(detail, panel.gpu_status_label.toolTip())
            self.assertTrue(panel.batch_status_label.wordWrap())
            self.assertTrue(panel.batch_info_label.wordWrap())
            self.assertLessEqual(panel.batch_status_label.maximumWidth(), 280)
            self.assertLessEqual(panel.batch_info_label.maximumWidth(), 280)
        finally:
            panel.close()

    def test_primary_buttons_can_shrink_in_fixed_width_panel(self):
        panel = ControlPanel()
        try:
            for button in (
                panel.process_btn,
                panel.quick_save_btn,
                panel.compare_btn,
                panel.auto_enhance_btn,
                panel.apply_to_all_btn,
                panel.save_current_btn,
                panel.save_all_btn,
            ):
                self.assertEqual(button.minimumWidth(), 0)
                self.assertEqual(button.sizePolicy().verticalPolicy(), QSizePolicy.Fixed)
        finally:
            panel.close()

    def test_model_comparison_dialog_imports_qdialog_and_opens(self):
        panel = ControlPanel()
        try:
            with unittest.mock.patch('src.ui.control_panel.QDialog.exec', return_value=0) as exec_dialog:
                panel._show_model_comparison()
                exec_dialog.assert_called_once()
        finally:
            panel.close()

    def test_shortcuts_dialog_has_readable_fixed_layout(self):
        dialog = ShortcutsDialog()
        try:
            self.assertGreaterEqual(dialog.minimumWidth(), 900)
            self.assertGreaterEqual(dialog.minimumHeight(), 560)
            key_labels = [label for label in dialog.findChildren(QLabel) if label.text() == 'Ctrl+O']
            self.assertTrue(key_labels)
            self.assertEqual(key_labels[0].width(), 142)
            self.assertGreaterEqual(key_labels[0].height(), 38)
            space_labels = [label for label in dialog.findChildren(QLabel) if label.text() == 'Space']
            self.assertTrue(space_labels)
            self.assertGreaterEqual(space_labels[0].height(), 38)
        finally:
            dialog.close()


if __name__ == '__main__':
    unittest.main()
