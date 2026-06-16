import tempfile
import unittest

from src.core.gpu_utils import GPUBackend, GPUInfo
from src.core.model_manager import ModelManager


class GpuFallbackTest(unittest.TestCase):
    def test_gpu_runtime_failure_switches_to_cpu_until_reenabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ModelManager(models_dir=tmp)
            manager._gpu_info = GPUInfo(
                available=True,
                backend=GPUBackend.CUDA,
                device_name='Test GPU',
                memory_total=8 * 1024 * 1024,
                memory_free=4 * 1024 * 1024,
                driver_version='test',
            )
            manager.use_gpu = True
            self.assertTrue(manager.use_gpu)

            manager._mark_gpu_runtime_failed(RuntimeError('CUBLAS_STATUS_NOT_INITIALIZED'))

            self.assertFalse(manager.use_gpu)
            self.assertTrue(manager.gpu_runtime_failed)
            self.assertIn('CUBLAS', manager.last_gpu_error)
            self.assertEqual(manager._providers_for_current_mode(), ['CPUExecutionProvider'])
            self.assertEqual(manager.device_status()['mode'], 'fallback')

            manager._gpu_info = GPUInfo(available=True, backend=GPUBackend.CUDA, device_name='Test GPU')
            manager.use_gpu = True
            self.assertFalse(manager.gpu_runtime_failed)
            self.assertTrue(manager.use_gpu)


if __name__ == '__main__':
    unittest.main()
