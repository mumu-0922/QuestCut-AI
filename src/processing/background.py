"""
Background Generator for QuestCut-AI
=================================
Solid, gradient, and image background generation.
"""
import logging
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import math
from ..utils.constants import GRADIENT_PRESETS, COLORS
logger = logging.getLogger(__name__)
class BackgroundType(Enum):
    TRANSPARENT = 'transparent'
    SOLID = 'solid'
    GRADIENT = 'gradient'
    IMAGE = 'image'
    CHECKERBOARD = 'checkerboard'
class GradientDirection(Enum):
    HORIZONTAL = 0
    VERTICAL = 90
    DIAGONAL_DOWN = 135
    DIAGONAL_UP = 45
@dataclass
class GradientSettings:
    color1: Union[str, Tuple[int, int, int]] = "#ffffff"
    color2: Union[str, Tuple[int, int, int]] = "#000000"
    direction: int = 135
    @classmethod
    def from_preset(cls, preset_name):
        preset = GRADIENT_PRESETS.get(preset_name, {})
        return cls(
            color1=preset.get('color1', '#ffffff'),
            color2=preset.get('color2', '#000000'),
            direction=preset.get('direction', 135))
class BackgroundGenerator:
    def __init__(self):
        self._cached_checkerboard = None
        self._checkerboard_size = None
    def create_transparent(self, size):
        return Image.new('RGBA', size, (0, 0, 0, 0))
    def create_solid(self, size, color):
        if isinstance(color, str):
            color = self._parse_color(color)
        return Image.new('RGBA', size, color + (255,))
    def create_gradient(self, size, color1, color2, direction):
        (width, height) = size
        if isinstance(color1, str):
            color1 = self._parse_color(color1)
        if isinstance(color2, str):
            color2 = self._parse_color(color2)
        img = np.zeros((height, width, 4), np.uint8)
        angle_rad = math.radians(direction)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        x = np.linspace(0, 1, width)
        y = np.linspace(0, 1, height)
        (xx, yy) = np.meshgrid(x, y)
        diag_len = abs(cos_a) + abs(sin_a)
        t = (xx * cos_a + yy * sin_a) / diag_len
        t = np.clip(t, 0, 1)
        for i in range(3):
            img[:, :, i] = (color1[i] * (1 - t) + color2[i] * t).astype(np.uint8)
        img[:, :, 3] = 255
        return Image.fromarray(img, 'RGBA')
    def create_gradient_from_preset(self, size, preset_name):
        settings = GradientSettings.from_preset(preset_name)
        return self.create_gradient(
            size, settings.color1, settings.color2, settings.direction)
    def create_checkerboard(self, size, square_size=16, color1=None, color2=None):
        if color1 is None:
            color1 = self._parse_color(COLORS['transparent_checker_light'])
        elif isinstance(color1, str):
            color1 = self._parse_color(color1)
        if color2 is None:
            color2 = self._parse_color(COLORS['transparent_checker_dark'])
        elif isinstance(color2, str):
            color2 = self._parse_color(color2)
        (width, height) = size
        if self._cached_checkerboard is not None and self._checkerboard_size == size:
            return self._cached_checkerboard.copy()
        rows = np.arange(height) // square_size
        cols = np.arange(width) // square_size
        checker = (rows[:, np.newaxis] + cols[np.newaxis, :]) % 2 == 0
        img = np.empty((height, width, 3), np.uint8)
        img[checker] = color1
        img[~checker] = color2
        result = Image.fromarray(img, 'RGB')
        self._cached_checkerboard = result.copy()
        self._checkerboard_size = size
        return result
    def create_from_image(self, size, source, fit_mode='cover', blur=0):
        (width, height) = size
        if fit_mode == 'cover':
            result = self._fit_cover(source, size)
        elif fit_mode == 'contain':
            result = self._fit_contain(source, size)
        elif fit_mode == 'stretch':
            result = source.resize(size, Image.LANCZOS)
        elif fit_mode == 'tile':
            result = self._fit_tile(source, size)
        else:
            logger.warning(f"Unknown fit mode: {fit_mode}, using cover")
            result = self._fit_cover(source, size)
        if result.mode != 'RGBA':
            result = result.convert('RGBA')
        if blur > 0:
            result = result.filter(ImageFilter.GaussianBlur(blur))
        return result
    def _fit_cover(self, source, size):
        (target_w, target_h) = size
        (source_w, source_h) = source.size
        scale = max(target_w / source_w, target_h / source_h)
        new_w = int(source_w * scale)
        new_h = int(source_h * scale)
        resized = source.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))
    def _fit_contain(self, source, size):
        (target_w, target_h) = size
        (source_w, source_h) = source.size
        scale = min(target_w / source_w, target_h / source_h)
        new_w = int(source_w * scale)
        new_h = int(source_h * scale)
        resized = source.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGBA', size, (0, 0, 0, 0))
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        canvas.paste(resized, (x, y))
        return canvas
    def _fit_tile(self, source, size):
        (target_w, target_h) = size
        (source_w, source_h) = source.size
        canvas = Image.new('RGBA', size, (0, 0, 0, 0))
        if source_w <= 0 or source_h <= 0:
            return canvas
        for y in range(0, target_h, source_h):
            for x in range(0, target_w, source_w):
                canvas.paste(source, (x, y))
        return canvas
    @staticmethod
    def _parse_color(color_str):
        color_str = color_str.lstrip('#')
        return tuple(
            int(color_str[i:i + 2], 16) for i in (0, 2, 4))
    @staticmethod
    def get_gradient_presets():
        return GRADIENT_PRESETS.copy()
    @staticmethod
    def get_preset_names():
        return list(GRADIENT_PRESETS.keys())
def create_solid_background(size, color):
    generator = BackgroundGenerator()
    return generator.create_solid(size, color)
def create_gradient_background(size, color1, color2, direction=135):
    generator = BackgroundGenerator()
    return generator.create_gradient(size, color1, color2, direction)
def create_checkerboard_background(size, square_size=16):
    generator = BackgroundGenerator()
    return generator.create_checkerboard(size, square_size)
