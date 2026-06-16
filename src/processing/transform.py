"""
Image Transform for QuestCut-AI
============================
Cropping, centering, resizing, and canvas fitting.
"""
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image
logger = logging.getLogger(__name__)
@dataclass
class BoundingBox:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)
    @property
    def right(self):
        return self.x + self.width
    @property
    def bottom(self):
        return self.y + self.height
class ImageTransform:
    @staticmethod
    def get_subject_bounds(image, threshold=30):
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        alpha = np.array(image.split()[3])
        rows = np.any(alpha > threshold, axis=1)
        cols = np.any(alpha > threshold, axis=0)
        if not np.any(rows) or not np.any(cols):
            return None
        (y_min, y_max) = np.where(rows)[0][[0, -1]]
        (x_min, x_max) = np.where(cols)[0][[0, -1]]
        return BoundingBox(
            x=int(x_min), y=int(y_min),
            width=int(x_max - x_min + 1),
            height=int(y_max - y_min + 1))
    def crop_to_subject(self, image, padding=0, padding_percent=0):
        bounds = self.get_subject_bounds(image)
        if bounds is None:
            return image
        if padding_percent > 0:
            pad_x = int(bounds.width * padding_percent)
            pad_y = int(bounds.height * padding_percent)
        else:
            pad_x = padding
            pad_y = padding
        left = max(0, bounds.x - pad_x)
        top = max(0, bounds.y - pad_y)
        right = min(image.width, bounds.right + pad_x)
        bottom = min(image.height, bounds.bottom + pad_y)
        return image.crop((left, top, right, bottom))
    def center_subject(self, image, canvas_size=None):
        if canvas_size is None:
            canvas_size = image.size
        bounds = self.get_subject_bounds(image)
        if bounds is None:
            if canvas_size != image.size:
                canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
                x = (canvas_size[0] - image.width) // 2
                y = (canvas_size[1] - image.height) // 2
                canvas.paste(image, (x, y), image)
                return canvas
            return image
        (subject_center_x, subject_center_y) = bounds.center
        canvas_center_x = canvas_size[0] // 2
        canvas_center_y = canvas_size[1] // 2
        offset_x = canvas_center_x - subject_center_x
        offset_y = canvas_center_y - subject_center_y
        canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        canvas.paste(image, (offset_x, offset_y), image)
        return canvas
    def fit_to_canvas(self, image, canvas_size, fit_mode='contain',
                      position='center'):
        (target_w, target_h) = canvas_size
        (source_w, source_h) = image.size
        if fit_mode == 'none':
            scaled = image
        elif fit_mode == 'fill':
            scaled = image.resize(canvas_size, Image.LANCZOS)
        elif fit_mode == 'cover':
            scale = max(target_w / source_w, target_h / source_h)
            new_size = (int(source_w * scale), int(source_h * scale))
            scaled = image.resize(new_size, Image.LANCZOS)
        else:
            scale = min(target_w / source_w, target_h / source_h)
            if scale >= 1:
                scaled = image
            else:
                new_size = (int(source_w * scale), int(source_h * scale))
                scaled = image.resize(new_size, Image.LANCZOS)
        canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        (x, y) = self._calculate_position(scaled.size, canvas_size, position)
        if fit_mode == 'cover':
            if scaled.width > target_w or scaled.height > target_h:
                crop_x = (scaled.width - target_w) // 2
                crop_y = (scaled.height - target_h) // 2
                scaled = scaled.crop((
                    crop_x, crop_y, crop_x + target_w, crop_y + target_h))
                (x, y) = (0, 0)
        if scaled.mode == 'RGBA':
            canvas.paste(scaled, (x, y), scaled)
        else:
            canvas.paste(scaled, (x, y))
        return canvas
    @staticmethod
    def _calculate_position(image_size, canvas_size, position):
        (img_w, img_h) = image_size
        (canvas_w, canvas_h) = canvas_size
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        if position == 'top':
            y = 0
        elif position == 'bottom':
            y = canvas_h - img_h
        elif position == 'left':
            x = 0
        elif position == 'right':
            x = canvas_w - img_w
        elif position == 'top-left':
            (x, y) = (0, 0)
        elif position == 'top-right':
            x = canvas_w - img_w
            y = 0
        elif position == 'bottom-left':
            x = 0
            y = canvas_h - img_h
        elif position == 'bottom-right':
            x = canvas_w - img_w
            y = canvas_h - img_h
        return (x, y)
    def resize_with_aspect(self, image, max_size, upscale=False):
        (width, height) = image.size
        scale = min(max_size / width, max_size / height)
        if scale >= 1 and not upscale:
            return image
        new_size = (int(width * scale), int(height * scale))
        return image.resize(new_size, Image.LANCZOS)
    def resize_to_width(self, image, target_width, upscale=False):
        (width, height) = image.size
        if width == target_width:
            return image
        if target_width > width and not upscale:
            return image
        scale = target_width / width
        new_height = int(height * scale)
        return image.resize((target_width, new_height), Image.LANCZOS)
    def resize_to_height(self, image, target_height, upscale=False):
        (width, height) = image.size
        if height == target_height:
            return image
        if target_height > height and not upscale:
            return image
        scale = target_height / height
        new_width = int(width * scale)
        return image.resize((new_width, target_height), Image.LANCZOS)
    def add_padding(self, image, padding, color=(0, 0, 0, 0)):
        new_size = (image.width + padding * 2, image.height + padding * 2)
        canvas = Image.new('RGBA', new_size, color)
        if image.mode == 'RGBA':
            canvas.paste(image, (padding, padding), image)
        else:
            canvas.paste(image, (padding, padding))
        return canvas
def crop_to_subject(image, padding=0):
    transform = ImageTransform()
    return transform.crop_to_subject(image, padding)
def center_subject(image, canvas_size=None):
    transform = ImageTransform()
    return transform.center_subject(image, canvas_size)
def fit_to_canvas(image, canvas_size, fit_mode='contain'):
    transform = ImageTransform()
    return transform.fit_to_canvas(image, canvas_size, fit_mode)
