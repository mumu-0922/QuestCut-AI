"""
GPU Utilities for QuestCut-AI
=========================
GPU detection and device management for ONNX Runtime.
"""
import logging
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum
logger = logging.getLogger(__name__)
class GPUBackend(Enum):
    CUDA = "cuda"
    DIRECTML = "directml"
    MPS = "mps"
    CPU = "cpu"
@dataclass
class GPUInfo:
    available: bool = False
    backend: GPUBackend = GPUBackend.CPU
    device_name: str = "CPU"
    memory_total: int = 0
    memory_free: int = 0
    driver_version: str = ""
def detect_cuda():
    if not shutil.which("nvidia-smi"):
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode != 0:
            return None
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            return None
        device_name = parts[0]
        memory_total = int(float(parts[1])) * 1024 * 1024
        memory_free = int(float(parts[2])) * 1024 * 1024
        driver_version = parts[3]
        logger.info(f"NVIDIA GPU detected: {device_name}")
        return GPUInfo(available=True, backend=GPUBackend.CUDA,
                       device_name=device_name, memory_total=memory_total,
                       memory_free=memory_free, driver_version=driver_version)
    except Exception:
        return None
def detect_directml():
    return None
_cached_gpu_info: Optional[GPUInfo] = None
def detect_gpu():
    global _cached_gpu_info
    if _cached_gpu_info is not None:
        return _cached_gpu_info
    gpu_info = detect_cuda()
    if gpu_info:
        _cached_gpu_info = gpu_info
        return gpu_info
    gpu_info = detect_directml()
    if gpu_info:
        _cached_gpu_info = gpu_info
        return gpu_info
    logger.info("No GPU detected, using CPU")
    _cached_gpu_info = GPUInfo()
    return _cached_gpu_info
def get_device(use_gpu=True):
    gpu_info = detect_gpu()
    if use_gpu and gpu_info.available:
        if gpu_info.backend == GPUBackend.CUDA:
            return "cuda"
        elif gpu_info.backend == GPUBackend.DIRECTML:
            return "directml"
    return "cpu"
_onnx_dlls_preloaded = False
_dll_directory_handles = []

def _add_nvidia_dll_directories():
    """Expose pip-installed NVIDIA DLL directories to Windows' loader."""
    import os
    import sysconfig
    site_packages = Path(sysconfig.get_paths().get("purelib", ""))
    nvidia_root = site_packages / "nvidia"
    dll_dirs = [
        nvidia_root / "cublas" / "bin",
        nvidia_root / "cuda_runtime" / "bin",
        nvidia_root / "cuda_nvrtc" / "bin",
        nvidia_root / "cudnn" / "bin",
        nvidia_root / "cufft" / "bin",
        nvidia_root / "curand" / "bin",
        nvidia_root / "nvjitlink" / "bin",
    ]
    existing_path = os.environ.get("PATH", "")
    prepend = []
    for dll_dir in dll_dirs:
        if not dll_dir.is_dir():
            continue
        path = str(dll_dir)
        prepend.append(path)
        if hasattr(os, "add_dll_directory"):
            try:
                _dll_directory_handles.append(os.add_dll_directory(path))
            except OSError as exc:
                logger.debug("Could not add DLL directory %s: %s", path, exc)
    if prepend:
        os.environ["PATH"] = os.pathsep.join(prepend + [existing_path])

def preload_onnx_gpu_dlls():
    """Preload pip-installed CUDA/cuDNN DLLs for ONNX Runtime on Windows."""
    global _onnx_dlls_preloaded
    if _onnx_dlls_preloaded:
        return
    try:
        _add_nvidia_dll_directories()
        import onnxruntime as ort
        preload = getattr(ort, "preload_dlls", None)
        if callable(preload):
            preload(cuda=True, cudnn=True, msvc=True, directory="")
        _onnx_dlls_preloaded = True
    except Exception as exc:
        logger.warning("Failed to preload ONNX Runtime GPU DLLs: %s", exc)

def get_onnx_providers():
    gpu_info = detect_gpu()
    providers = ["CPUExecutionProvider"]
    try:
        import onnxruntime as ort
        if gpu_info.available and gpu_info.backend == GPUBackend.CUDA:
            preload_onnx_gpu_dlls()
        available_providers = set(ort.get_available_providers())
    except Exception:
        available_providers = {"CPUExecutionProvider"}

    if gpu_info.available:
        if (gpu_info.backend == GPUBackend.CUDA
                and "CUDAExecutionProvider" in available_providers):
            providers.insert(0, "CUDAExecutionProvider")
        elif (gpu_info.backend == GPUBackend.DIRECTML
              and "DmlExecutionProvider" in available_providers):
            providers.insert(0, "DmlExecutionProvider")
    return providers


def clear_gpu_memory():
    """Clear GPU memory caches and release unused resources."""
    import gc
    gc.collect()
    try:
        import onnxruntime as ort
        # Release all ONNX Runtime sessions and internal allocations
        ort.clear_staging_area()
    except Exception:
        pass
    logger.debug("GPU memory cleared")
