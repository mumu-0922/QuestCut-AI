import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from src.ui.control_panel import ControlPanel
from src.utils.i18n import set_language


class UiI18nTooltipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        set_language('en')

    def test_control_panel_hover_texts_follow_simplified_chinese(self):
        set_language('zh_CN')
        panel = ControlPanel()
        try:
            tooltips = '\n'.join(
                widget.toolTip()
                for widget in (
                    panel.model_help_btn,
                    panel.model_combo,
                    panel.gpu_check,
                    panel.gpu_retry_btn,
                    panel.auto_process_check,
                    panel.process_btn,
                    panel.quick_save_btn,
                    panel.compare_btn,
                    panel.auto_enhance_btn,
                    panel.apply_to_all_btn,
                    panel.save_current_btn,
                    panel.save_all_btn,
                    panel.smart_crop_btn,
                    panel.reset_position_btn,
                )
            )

            for forbidden in (
                'Click to see model comparison',
                'Best quality (products, complex edges)',
                'Use CUDA acceleration when available',
                'Automatically remove background',
                'Save as PNG with transparent background',
                'Drag the slider to compare',
                'One click to perfection',
                'Copy current background',
                'Export all processed images',
                'Automatically centers and scales',
                'Reset all position transforms',
            ):
                self.assertNotIn(forbidden, tooltips)

            for expected in (
                '点击查看模型对比',
                '最佳质量',
                '可用时使用 CUDA 加速',
                '拖入图片后自动移除背景',
                '保存为透明背景 PNG',
                '拖动滑块对比处理前后',
                '一键优化到位',
                '把当前背景、阴影和位置设置复制',
                '把所有已处理图片导出到文件夹',
                '自动居中并缩放主体',
                '重置所有位置变换',
            ):
                self.assertIn(expected, tooltips)
        finally:
            panel.close()

    def test_control_panel_labels_follow_simplified_chinese_on_creation(self):
        set_language('zh_CN')
        panel = ControlPanel()
        try:
            self.assertEqual(panel.process_btn.text().strip(), '移除背景')
            self.assertEqual(panel.quick_save_btn.text(), '快速保存 PNG')
            self.assertEqual(panel.apply_to_all_btn.text(), '应用设置到全部')
            self.assertEqual(panel.smart_crop_btn.text(), '智能裁剪')
            self.assertEqual(panel.bg_type_label.text(), '类型：')
            label_texts = [label.text() for label in panel.findChildren(type(panel.bg_type_label))]
            self.assertIn('X：', label_texts)
            self.assertIn('Y：', label_texts)
            self.assertEqual(panel.progress_bar.format(), '处理中... %p%')
        finally:
            panel.close()


if __name__ == '__main__':
    unittest.main()
