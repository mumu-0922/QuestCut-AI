'''
Processing modules for QuestCut-AI
===============================
Image processing operations: masks, shadows, backgrounds, transforms, export.
'''
from .mask_ops import MaskOperations, BrushStroke, BrushMode, refine_mask_edges, apply_brush_stroke, combine_masks
from .shadow import ShadowGenerator, ShadowSettings, create_drop_shadow
from .background import BackgroundGenerator, BackgroundType, create_solid_background, create_gradient_background, create_checkerboard_background
from .transform import ImageTransform, BoundingBox, crop_to_subject, center_subject, fit_to_canvas
from .export import ExportManager, ExportSettings, ExportResult, export_single, export_for_platform
from .cache import ProcessingCache, CacheEntry, get_processing_cache
from .batch_queue import BatchQueue, BatchWorker, QueueItem, QueueProgress, QueueStatus, ItemStatus
from .auto_enhance import AutoEnhance, EnhanceResult, MaskAnalysis, auto_enhance_image
from .progressive_preview import ProgressivePreview, PreviewResult, PreviewWorker
