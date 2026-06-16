'''
Core modules for QuestCut-AI
=========================
AI model management and processing logic.
'''
from .gpu_utils import GPUInfo, GPUBackend, detect_gpu, get_device, get_onnx_providers, preload_onnx_gpu_dlls, clear_gpu_memory
from .model_manager import ModelManager, ModelType, ModelStatus, get_model_manager
from .background_remover import BackgroundRemover, remove_background_simple
from .portrait_mode import PortraitMode
from .resilient_loader import ResilientLoader, LoaderResult, LoaderError, LoaderState, ModelLoadingManager, get_loading_manager, with_retry
from .memory_manager import MemoryManager, MemoryStats, get_memory_manager, get_memory_stats, cleanup_memory, processing_context
