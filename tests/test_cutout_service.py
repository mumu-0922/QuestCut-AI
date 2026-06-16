import tempfile
import unittest
from pathlib import Path

from PIL import Image

from src.services.cutout_service import CutoutResult, CutoutService


class FakeRemover:
    def remove_background_sync(self, image, model_name=None):
        result = image.convert('RGBA')
        mask = Image.new('L', result.size, 128)
        result.putalpha(mask)
        return result, mask


class FakePortrait:
    def process(self, image, async_mode=False):
        return Image.new('L', image.size, 200)

    def apply_matte(self, image, matte):
        result = image.convert('RGBA')
        result.putalpha(matte)
        return result


class CutoutServiceTest(unittest.TestCase):
    def make_service(self):
        service = CutoutService()
        service._remover = FakeRemover()
        service._portrait = FakePortrait()
        return service

    def test_available_models_include_runtime_keys(self):
        models = CutoutService.available_models()
        self.assertIn('birefnet', models)
        self.assertIn('birefnet_portrait', models)
        self.assertIn('modnet', models)

    def test_remove_background_uses_rembg_model_and_returns_mask(self):
        service = self.make_service()
        source = Image.new('RGB', (4, 4), (10, 20, 30))

        result = service.remove_background(source, model_key='birefnet')

        self.assertEqual(result.model_key, 'birefnet')
        self.assertEqual(result.image.mode, 'RGBA')
        self.assertEqual(result.mask.mode, 'L')
        self.assertEqual(result.mask.getpixel((0, 0)), 128)

    def test_modnet_path_applies_portrait_matte(self):
        service = self.make_service()
        source = Image.new('RGB', (4, 4), (10, 20, 30))

        result = service.remove_background(source, model_key='modnet')

        self.assertEqual(result.model_key, 'modnet')
        self.assertEqual(result.mask.getpixel((0, 0)), 200)
        self.assertEqual(result.image.getpixel((0, 0))[3], 200)

    def test_save_result_flattens_jpeg_and_preserves_png_alpha(self):
        service = self.make_service()
        with tempfile.TemporaryDirectory() as tmp:
            image = Image.new('RGBA', (3, 3), (255, 0, 0, 128))
            result = CutoutResult(image=image, mask=Image.new('L', image.size, 128), model_key='birefnet')
            png = service.save_result(result, Path(tmp) / 'out.png')
            jpg = service.save_result(result, Path(tmp) / 'out.jpg')

            with Image.open(png) as saved_png:
                self.assertEqual(saved_png.mode, 'RGBA')
            with Image.open(jpg) as saved_jpg:
                self.assertEqual(saved_jpg.mode, 'RGB')

    def test_process_files_writes_outputs(self):
        service = self.make_service()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'sample.png'
            out = Path(tmp) / 'out'
            Image.new('RGBA', (3, 3), (1, 2, 3, 255)).save(src)

            written = service.process_files([src], out, model_key='birefnet')

            self.assertEqual(len(written), 1)
            self.assertTrue(written[0].exists())
            self.assertEqual(written[0].name, 'sample_nobg.png')

    def test_rejects_unknown_model_and_format(self):
        service = self.make_service()
        with self.assertRaises(ValueError):
            service.remove_background(Image.new('RGB', (1, 1)), model_key='missing')
        with self.assertRaises(ValueError):
            service.validate_output_format('bmp')


if __name__ == '__main__':
    unittest.main()
