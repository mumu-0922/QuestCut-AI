import unittest

from src.utils.i18n import set_language, tr


class I18nSmokeTest(unittest.TestCase):
    def tearDown(self):
        set_language('en')

    def test_canvas_and_gpu_terms_are_translated(self):
        set_language('zh_CN')
        self.assertEqual(tr('Original'), '原图')
        self.assertEqual(tr('Result'), '结果')
        self.assertEqual(tr('Use GPU acceleration'), '使用 GPU 加速')
        self.assertEqual(tr('GPU active'), 'GPU 已启用')
        self.assertEqual(tr('Saving batch images...'), '正在保存批量图片...')
        self.assertEqual(tr('Drop Image Here'), '把图片拖到这里')
        self.assertEqual(tr('Release to Process'), '松开开始处理')
        self.assertEqual(tr('Images (*.png *.jpg *.jpeg *.webp)'), '图片 (*.png *.jpg *.jpeg *.webp)')
        self.assertEqual(tr('Images (*.png *.jpg *.jpeg *.webp *.bmp)'), '图片 (*.png *.jpg *.jpeg *.webp *.bmp)')
        self.assertEqual(tr('Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif)'), '图片 (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif)')
        self.assertEqual(tr('X:'), 'X：')
        self.assertEqual(tr('Y:'), 'Y：')


if __name__ == '__main__':
    unittest.main()
