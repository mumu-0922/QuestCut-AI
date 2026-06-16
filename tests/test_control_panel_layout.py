import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QSizePolicy

from src.ui.control_panel import ControlPanel


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


if __name__ == '__main__':
    unittest.main()
