"""
Shadow Generator for QuestCut-AI
=============================
Drop shadow generation and application.
"""
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageFilter
import math
from ..utils.constants import SHADOW_PRESETS
logger = logging.getLogger(__name__)
@dataclass
class ShadowSettings:
    enabled: bool = True
    blur: int = 25
    opacity: int = 30
    distance: int = 8
    angle: int = 135
    color: str = '#000000'
    def get_offset(self):
        angle_rad = math.radians(self.angle)
        offset_x = int(self.distance * math.cos(angle_rad))
        offset_y = int(-self.distance * math.sin(angle_rad))
        return (offset_x, offset_y)
class ShadowGenerator:
    def __init__(self, settings=None):
        self.settings = settings if settings else ShadowSettings()
    def generate(self, image, settings=None):
        if settings is None:
            settings = self.settings
        if not settings.enabled:
            return Image.new('RGBA', image.size, (0, 0, 0, 0))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        alpha = image.split()[3]
        shadow_color = self._parse_color(settings.color)
        shadow = Image.new('RGBA', image.size, shadow_color + (0,))
        shadow.putalpha(alpha)
        if settings.blur > 0:
            shadow = shadow.filter(ImageFilter.GaussianBlur(settings.blur))
        if settings.opacity < 100:
            shadow_alpha = shadow.split()[3]
            factor = settings.opacity / 100
            lut = [int(i * factor) for i in range(256)]
            shadow_alpha = shadow_alpha.point(lut)
            shadow.putalpha(shadow_alpha)
        return shadow
    def apply_to_image(self, image, background=None, settings=None):
        if settings is None:
            settings = self.settings
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        (offset_x, offset_y) = settings.get_offset()
        padding = settings.blur + max(abs(offset_x), abs(offset_y))
        new_width = image.width + padding * 2
        new_height = image.height + padding * 2
        if background is None:
            canvas = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        elif background.size != (new_width, new_height):
            canvas = background.resize((new_width, new_height), Image.LANCZOS)
        else:
            canvas = background.copy()
        if canvas.mode != 'RGBA':
            canvas = canvas.convert('RGBA')
        shadow = self.generate(image, settings)
        shadow_x = padding + offset_x
        shadow_y = padding + offset_y
        image_x = padding
        image_y = padding
        if settings.enabled:
            canvas.paste(shadow, (shadow_x, shadow_y), shadow)
        canvas.paste(image, (image_x, image_y), image)
        return canvas
    def apply_to_image_no_expand(self, image, background=None, settings=None):
        if settings is None:
            settings = self.settings
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        if background is None:
            canvas = Image.new('RGBA', image.size, (0, 0, 0, 0))
        elif background.size != image.size:
            canvas = background.resize(image.size, Image.LANCZOS)
        else:
            canvas = background.copy()
        if canvas.mode != 'RGBA':
            canvas = canvas.convert('RGBA')
        if settings.enabled:
            shadow = self.generate(image, settings)
            (offset_x, offset_y) = settings.get_offset()
            shadow_canvas = Image.new('RGBA', image.size, (0, 0, 0, 0))
            sx = max(0, -offset_x)
            sy = max(0, -offset_y)
            dx = max(0, offset_x)
            dy = max(0, offset_y)
            sw = min(shadow.width - sx, image.size[0] - dx)
            sh = min(shadow.height - sy, image.size[1] - dy)
            if sw > 0 and sh > 0:
                cropped = shadow.crop((sx, sy, sx + sw, sy + sh))
                shadow_canvas.paste(cropped, (dx, dy), cropped)
            canvas = Image.alpha_composite(canvas, shadow_canvas)
        canvas = Image.alpha_composite(canvas, image)
        return canvas
    @staticmethod
    def _parse_color(color_str):
        color_str = color_str.lstrip('#')
        return tuple(
            int(color_str[i:i + 2], 16) for i in (0, 2, 4))
    @staticmethod
    def get_presets():
        return SHADOW_PRESETS.copy()
    @staticmethod
    def get_preset_names():
        return list(SHADOW_PRESETS.keys())
def create_drop_shadow(image, blur=25, opacity=30, distance=8, angle=135,
                       color='#000000'):
    settings = ShadowSettings(
        enabled=True, blur=blur, opacity=opacity,
        distance=distance, angle=angle, color=color)
    generator = ShadowGenerator(settings)
    return generator.generate(image)
