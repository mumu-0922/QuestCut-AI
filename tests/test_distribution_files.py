import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DistributionFilesTest(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding='utf-8')

    def test_docker_files_use_web_entrypoint_and_safe_defaults(self):
        dockerfile = self.read('Dockerfile')
        compose = self.read('docker-compose.yml')
        dockerignore = self.read('.dockerignore')

        self.assertIn('scripts/run_web.py', dockerfile)
        self.assertIn('127.0.0.1:7860:7860', compose)
        self.assertIn('/health', compose)
        self.assertIn('./models:/app/models:ro', compose)
        self.assertIn('*.onnx', dockerignore)

    def test_run_web_adds_repo_root_to_python_path(self):
        run_web = self.read('scripts/run_web.py')
        self.assertIn('sys.path.insert(0, str(ROOT))', run_web)
        self.assertIn('app_dir=str(ROOT)', run_web)

    def test_readme_lists_three_distribution_commands(self):
        readme = self.read('README.md')
        self.assertIn('python scripts/build_portable.py --version 1.0.1', readme)
        self.assertIn('python scripts/run_web.py --host 127.0.0.1 --port 7860', readme)
        self.assertIn('docker compose up --build', readme)


if __name__ == '__main__':
    unittest.main()
