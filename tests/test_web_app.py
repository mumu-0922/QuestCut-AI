import unittest
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from src.web.app import _normalize_filename, _service, create_app


class FakeService:
    @staticmethod
    def available_models():
        return {
            'birefnet': {
                'name': 'BiRefNet',
                'display_name': 'BiRefNet (Best Quality)',
                'description': 'test model',
                'size': '~928MiB',
            }
        }

    @staticmethod
    def validate_output_format(output_format):
        fmt = (output_format or 'png').lower().lstrip('.')
        if fmt not in {'png', 'jpg', 'jpeg', 'webp'}:
            raise ValueError('Unsupported output format')
        return 'jpg' if fmt == 'jpeg' else fmt

    @staticmethod
    def validate_model(model_key):
        if model_key != 'birefnet':
            raise ValueError('Unknown model')
        return model_key

    def remove_background(self, image, model_key='birefnet'):
        from src.services.cutout_service import CutoutResult
        result = image.convert('RGBA')
        alpha = Image.new('L', result.size, 128)
        result.putalpha(alpha)
        return CutoutResult(image=result, mask=alpha, model_key=model_key)


class WebAppTest(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.dependency_overrides[_service] = lambda: FakeService()
        self.client = TestClient(app)

    def make_png(self):
        data = BytesIO()
        Image.new('RGB', (3, 3), (10, 20, 30)).save(data, 'PNG')
        data.seek(0)
        return data

    def test_health_models_and_index(self):
        self.assertEqual(self.client.get('/health').json()['status'], 'ok')
        models = self.client.get('/api/models').json()['models']
        self.assertEqual(models[0]['key'], 'birefnet')
        index = self.client.get('/')
        self.assertEqual(index.status_code, 200)
        self.assertIn('QuestCut-AI Web', index.text)

    def test_normalize_filename_is_header_safe_ascii(self):
        self.assertEqual(_normalize_filename('sample image.png'), 'sample_image')
        self.assertEqual(_normalize_filename('中文图片.png'), 'image')

    def test_remove_background_returns_image(self):
        resp = self.client.post(
            '/api/remove-background',
            data={'model_key': 'birefnet', 'output_format': 'png'},
            files={'file': ('sample.png', self.make_png(), 'image/png')},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['content-type'], 'image/png')
        self.assertIn('sample_nobg.png', resp.headers['content-disposition'])
        with Image.open(BytesIO(resp.content)) as image:
            self.assertEqual(image.mode, 'RGBA')

    def test_rejects_bad_model_and_type(self):
        bad_model = self.client.post(
            '/api/remove-background',
            data={'model_key': 'missing', 'output_format': 'png'},
            files={'file': ('sample.png', self.make_png(), 'image/png')},
        )
        self.assertEqual(bad_model.status_code, 400)

        bad_type = self.client.post(
            '/api/remove-background',
            data={'model_key': 'birefnet', 'output_format': 'png'},
            files={'file': ('sample.txt', b'not image', 'text/plain')},
        )
        self.assertEqual(bad_type.status_code, 400)


if __name__ == '__main__':
    unittest.main()
