import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_portable


class BuildPortableTest(unittest.TestCase):
    def test_ensure_models_reports_missing_without_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(SystemExit) as ctx:
                build_portable.ensure_models(root)
            self.assertIn('Missing bundled model files', str(ctx.exception))

    def test_ensure_models_allows_skip_and_returns_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = build_portable.ensure_models(Path(tmp), skip=True)
            self.assertEqual(len(missing), len(build_portable.REQUIRED_MODEL_FILES))

    def test_collect_nvidia_cuda_binaries_preserves_package_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            dll = site / 'nvidia' / 'cublas' / 'bin' / 'cublas64_12.dll'
            dll.parent.mkdir(parents=True)
            dll.write_bytes(b'dll')

            binaries = build_portable.collect_nvidia_cuda_binaries(site)

            self.assertEqual(binaries, [(dll, Path('nvidia/cublas/bin'))])

    def test_pyinstaller_add_binary_arg_uses_platform_separator(self):
        arg = build_portable.pyinstaller_add_binary_arg(Path('a.dll'), Path('nvidia/cublas/bin'))
        self.assertIn(str(Path('a.dll')), arg)
        self.assertIn(str(Path('nvidia/cublas/bin')), arg)

    def test_create_zip_contains_portable_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work_dir = root / 'dist' / build_portable.APP_NAME
            work_dir.mkdir(parents=True)
            (work_dir / f'{build_portable.APP_NAME}.exe').write_text('exe', encoding='utf-8')
            (work_dir / 'README_PORTABLE.txt').write_text('readme', encoding='utf-8')

            zip_path = build_portable.create_zip(root, work_dir, '9.9.9')

            self.assertTrue(zip_path.exists())
            import zipfile
            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            self.assertIn(f'{build_portable.APP_NAME}/{build_portable.APP_NAME}.exe', names)
            self.assertIn(f'{build_portable.APP_NAME}/README_PORTABLE.txt', names)

    def test_ensure_pyinstaller_error_message_is_actionable(self):
        with patch.dict('sys.modules', {'PyInstaller': None}):
            with self.assertRaises(SystemExit) as ctx:
                build_portable.ensure_pyinstaller()
            self.assertIn('python -m pip install pyinstaller', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
