"""
Auto-Enhance for QuestCut-AI
=========================
Automatic mask optimization and subject centering.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import numpy as np
from PIL import Image
import cv2
from .transform import ImageTransform
from .mask_ops import MaskOperations
logger = logging.getLogger(__name__)
@dataclass
class MaskAnalysis:
    edge_smoothness: float = 0.0
    edge_sharpness: float = 0.0
    coverage_ratio: float = 0.0
    has_fringe: bool = False
    suggested_sharpen: float = 0.0
    suggested_expand: int = 0
    suggested_feather: int = 0
    suggested_defringe: int = 0
@dataclass
class EnhanceResult:
    enhanced_mask: np.ndarray = None
    enhanced_image: Image.Image = None
    settings_applied: dict = None
    quality_score: float = 0.0
class AutoEnhance:
    def __init__(self):
        self._transform = ImageTransform()
        self._mask_ops = MaskOperations()
    def analyze_mask(self, mask):
        grad_x = cv2.Sobel(mask, cv2.CV_64F, 1, 0, 3)
        grad_y = cv2.Sobel(mask, cv2.CV_64F, 0, 1, 3)
        gradient_magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        edge_threshold = 30
        edge_mask = gradient_magnitude > edge_threshold
        if np.any(edge_mask):
            edge_variance = np.var(gradient_magnitude[edge_mask])
            edge_smoothness = 1 - min(edge_variance / 10000, 1)
        else:
            edge_smoothness = 1
        if np.any(edge_mask):
            mean_gradient = np.mean(gradient_magnitude[edge_mask])
            edge_sharpness = min(mean_gradient / 100, 1)
        else:
            edge_sharpness = 1
        total_pixels = mask.size
        foreground_pixels = np.sum(mask > 127)
        coverage_ratio = foreground_pixels / total_pixels
        transition_low = np.sum((mask > 20) & (mask < 235))
        transition_ratio = transition_low / total_pixels
        has_fringe = transition_ratio > 0.05
        suggested_sharpen = 0.0
        suggested_expand = 0
        suggested_feather = 0
        suggested_defringe = 0
        if edge_sharpness < 0.5:
            suggested_sharpen = 0.3 * (1 - edge_sharpness)
        if edge_smoothness < 0.6:
            suggested_feather = int(3 * (1 - edge_smoothness))
        if has_fringe:
            suggested_defringe = 2
        return MaskAnalysis(
            edge_smoothness=edge_smoothness,
            edge_sharpness=edge_sharpness,
            coverage_ratio=coverage_ratio,
            has_fringe=has_fringe,
            suggested_sharpen=suggested_sharpen,
            suggested_expand=suggested_expand,
            suggested_feather=suggested_feather,
            suggested_defringe=suggested_defringe)
    def enhance_mask(self, mask, analysis=None):
        if analysis is None:
            analysis = self.analyze_mask(mask)
        settings = {
            'sharpen': analysis.suggested_sharpen,
            'expand': analysis.suggested_expand,
            'feather': analysis.suggested_feather,
            'defringe': analysis.suggested_defringe}
        enhanced = self._mask_ops.refine_edges(
            mask, settings['sharpen'], settings['expand'],
            settings['feather'], settings['defringe'])
        return (enhanced, settings)
    def auto_enhance(self, image, mask, center_subject=True):
        analysis = self.analyze_mask(mask)
        (enhanced_mask, settings) = self.enhance_mask(mask, analysis)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        result_image = image.copy()
        mask_pil = Image.fromarray(enhanced_mask, 'L')
        if mask_pil.size != image.size:
            mask_pil = mask_pil.resize(image.size, Image.LANCZOS)
        result_image.putalpha(mask_pil)
        if center_subject:
            result_image = self._transform.center_subject(result_image)
        quality_score = self._calculate_quality_score(analysis)
        return EnhanceResult(
            enhanced_mask=enhanced_mask,
            enhanced_image=result_image,
            settings_applied=settings,
            quality_score=quality_score)
    def _calculate_quality_score(self, analysis):
        smoothness_weight = 0.3
        sharpness_weight = 0.3
        coverage_weight = 0.2
        fringe_penalty = 0.2
        score = (analysis.edge_smoothness * smoothness_weight +
                 analysis.edge_sharpness * sharpness_weight +
                 min(analysis.coverage_ratio * 2, 1) * coverage_weight)
        if analysis.has_fringe:
            score -= fringe_penalty
        return max(0, min(1, score))
    def suggest_improvements(self, mask):
        analysis = self.analyze_mask(mask)
        suggestions = {}
        if analysis.edge_sharpness < 0.4:
            suggestions['sharpness'] = (
                'Edges appear soft. Consider increasing edge sharpness '
                'for a cleaner cutout.')
        if analysis.edge_smoothness < 0.5:
            suggestions['smoothness'] = (
                'Edges appear jagged. A small amount of feathering '
                'will smooth the edges.')
        if analysis.has_fringe:
            suggestions['fringe'] = (
                'Color fringe detected around edges. Defringe will '
                'remove unwanted color halos.')
        if analysis.coverage_ratio < 0.1:
            suggestions['coverage'] = (
                'Subject covers a small portion of the image. '
                'Consider cropping to subject.')
        if analysis.coverage_ratio > 0.9:
            suggestions['coverage'] = (
                'Subject fills most of the image. Ensure edges are '
                'not being cut off.')
        return suggestions
def auto_enhance_image(image, mask, center=True):
    enhancer = AutoEnhance()
    return enhancer.auto_enhance(image, mask, center)
