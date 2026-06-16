import tempfile
import unittest
from pathlib import Path

from src.core.model_manager import ModelManager


class ModelPathTest(unittest.TestCase):
    def test_models_directory_is_preferred_over_legacy_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preferred = root / 'models' / 'rembg'
            legacy = root / '_decompiled_stdlib_backup' / 'models' / 'rembg'
            preferred.mkdir(parents=True)
            legacy.mkdir(parents=True)
            (preferred / 'birefnet-general.onnx').write_text('preferred', encoding='utf-8')
            (legacy / 'birefnet-general.onnx').write_text('legacy', encoding='utf-8')

            manager = ModelManager(models_dir=root / 'user_models')
            manager._bundled_models_dirs = [root / 'models', root / '_decompiled_stdlib_backup' / 'models']

            path = Path(manager._find_model_file('birefnet'))
            self.assertEqual(path.read_text(encoding='utf-8'), 'preferred')


if __name__ == '__main__':
    unittest.main()
