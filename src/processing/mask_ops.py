"""
Mask Operations for QuestCut-AI
============================
Edge refinement, brush tools, and mask manipulation.
"""
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image
import cv2
logger = logging.getLogger(__name__)
class BrushMode(Enum):
    ADD = 'add'
    REMOVE = 'remove'
@dataclass
class BrushStroke:
    points: List[Tuple[int, int]] = None
    radius: int = 10
    mode: BrushMode = BrushMode.ADD
    hardness: float = 1.0
class MaskOperations:
    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 20
    def refine_edges(self, mask, sharpen=0.0, expand=0, feather=0, defringe=0):
        result = mask.copy()
        original_area = int(np.count_nonzero(mask > 128))
        if expand != 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            iterations = abs(expand)
            if expand > 0:
                result = cv2.dilate(result, kernel, iterations)
            else:
                result = cv2.erode(result, kernel, iterations)
                if original_area > 0:
                    remaining = int(np.count_nonzero(result > 128))
                    if remaining < original_area * 0.2 and iterations > 1:
                        iterations -= 1
                        result = cv2.erode(mask.copy(), kernel, iterations)
                        remaining = int(np.count_nonzero(result > 128))
                        if remaining < original_area * 0.2:
                            result = mask.copy()
        if defringe > 0:
            kernel_size = defringe * 2 + 1
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            temp = cv2.erode(result, kernel, 1)
            small_kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (max(1, defringe), max(1, defringe)))
            result = cv2.dilate(temp, small_kernel, 1)
        if feather > 0:
            ksize = feather * 2 + 1
            result = cv2.GaussianBlur(result, (ksize, ksize), 0)
        if sharpen != 0:
            blurred = cv2.GaussianBlur(
                result.astype(np.float32), (0, 0), 3)
            if sharpen > 0:
                sharpened = cv2.addWeighted(
                    result.astype(np.float32), 1 + sharpen,
                    blurred, -sharpen, 0)
            else:
                alpha = min(abs(sharpen), 0.5)
                sharpened = cv2.addWeighted(
                    result.astype(np.float32), 1 - alpha,
                    blurred, alpha, 0)
            result = np.clip(sharpened, 0, 255).astype(np.uint8)
        return result
    def apply_brush(self, mask, stroke, save_undo=True):
        if save_undo:
            self._save_undo(mask)
        result = mask.copy()
        brush_mask = np.zeros_like(mask)
        for i in range(len(stroke.points)):
            (x, y) = stroke.points[i]
            cv2.circle(brush_mask, (x, y), stroke.radius, 255, -1)
            if i > 0:
                (x_prev, y_prev) = stroke.points[i - 1]
                cv2.line(brush_mask, (x_prev, y_prev), (x, y),
                         255, stroke.radius * 2)
        if stroke.hardness < 1:
            blur_amount = int((1 - stroke.hardness) * stroke.radius)
            if blur_amount > 0:
                ksize = blur_amount * 2 + 1
                brush_mask = cv2.GaussianBlur(
                    brush_mask, (ksize, ksize), 0)
        if stroke.mode == BrushMode.ADD:
            result = np.maximum(result, brush_mask)
        else:
            result = np.minimum(result, 255 - brush_mask)
        return result
    def _save_undo(self, mask):
        self._undo_stack.append(mask.copy())
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
    def undo(self, current_mask):
        if not self._undo_stack:
            return None
        self._redo_stack.append(current_mask.copy())
        if len(self._redo_stack) > self._max_undo:
            self._redo_stack.pop(0)
        return self._undo_stack.pop()
    def redo(self, current_mask):
        if not self._redo_stack:
            return None
        self._undo_stack.append(current_mask.copy())
        return self._redo_stack.pop()
    def can_undo(self):
        return len(self._undo_stack) > 0
    def can_redo(self):
        return len(self._redo_stack) > 0
    def clear_history(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
    @staticmethod
    def combine_masks(mask1, mask2, operation):
        if operation == 'union':
            return np.maximum(mask1, mask2)
        elif operation == 'intersection':
            return np.minimum(mask1, mask2)
        elif operation == 'difference':
            return np.clip(
                mask1.astype(np.int32) - mask2.astype(np.int32),
                0, 255).astype(np.uint8)
        elif operation == 'xor':
            return np.abs(
                mask1.astype(np.int32) - mask2.astype(np.int32)
            ).astype(np.uint8)
        raise ValueError(f"Unknown operation: {operation}")
    @staticmethod
    def invert_mask(mask):
        return 255 - mask
    @staticmethod
    def threshold_mask(mask, threshold, soft=False):
        if soft:
            mask_float = mask.astype(np.float32)
            steepness = 0.1
            result = 255 / (1 + np.exp(
                -steepness * (mask_float - threshold)))
            return result.astype(np.uint8)
        return np.where(mask >= threshold, 255, 0).astype(np.uint8)
    @staticmethod
    def get_mask_bounds(mask):
        rows = np.any(mask > 0, axis=1)
        cols = np.any(mask > 0, axis=0)
        if not np.any(rows) or not np.any(cols):
            return None
        (y_min, y_max) = np.where(rows)[0][[0, -1]]
        (x_min, x_max) = np.where(cols)[0][[0, -1]]
        return (int(x_min), int(y_min),
                int(x_max - x_min + 1), int(y_max - y_min + 1))
    @staticmethod
    def mask_to_pil(mask):
        return Image.fromarray(mask, 'L')
    @staticmethod
    def pil_to_mask(image):
        if image.mode != 'L':
            image = image.convert('L')
        return np.array(image)
def refine_mask_edges(mask, sharpen=0.0, expand=0, feather=0, defringe=0):
    ops = MaskOperations()
    return ops.refine_edges(mask, sharpen, expand, feather, defringe)
def apply_brush_stroke(mask, points, radius=10, mode='add', hardness=1.0):
    ops = MaskOperations()
    brush_mode = BrushMode.ADD if mode == 'add' else BrushMode.REMOVE
    stroke = BrushStroke(
        points=points, radius=radius, mode=brush_mode, hardness=hardness)
    return ops.apply_brush(mask, stroke, save_undo=False)
def combine_masks(mask1, mask2, operation):
    return MaskOperations.combine_masks(mask1, mask2, operation)
