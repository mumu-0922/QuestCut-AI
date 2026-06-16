"""
Image Utilities for QuestCut-AI
============================
Conversion utilities between PIL, NumPy, and Qt image formats.
"""
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Union
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
def pil_to_qimage(pil_image):
    """Convert a PIL Image to a QImage."""
    if pil_image.mode == 'RGB':
        pil_image = pil_image.convert('RGBA')
    elif pil_image.mode == 'L':
        pil_image = pil_image.convert('RGBA')
    elif pil_image.mode == 'P':
        pil_image = pil_image.convert('RGBA')
    elif pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')
    data = pil_image.tobytes('raw', 'RGBA')
    qimage = QImage(data, pil_image.width, pil_image.height, pil_image.width * 4, QImage.Format_RGBA8888)
    return qimage.copy()
def qimage_to_pil(qimage):
    """Convert a QImage to a PIL Image."""
    qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
    width = qimage.width()
    height = qimage.height()
    bytes_per_line = qimage.bytesPerLine()
    ptr = qimage.bits()
    ptr.setsize(height * bytes_per_line)
    arr = np.array(ptr).reshape(height, bytes_per_line)
    arr = arr[:, :width * 4].reshape(height, width, 4)
    return Image.fromarray(arr, 'RGBA')
def pil_to_qpixmap(pil_image):
    """Convert a PIL Image to a QPixmap."""
    qimage = pil_to_qimage(pil_image)
    return QPixmap.fromImage(qimage)
def qpixmap_to_pil(qpixmap):
    """Convert a QPixmap to a PIL Image."""
    qimage = qpixmap.toImage()
    return qimage_to_pil(qimage)
def numpy_to_qimage(arr):
    """Convert a NumPy array to a QImage."""
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        height, width = arr.shape
        bytes_per_line = width
        return QImage(arr.data, width, height, bytes_per_line, QImage.Format_Grayscale8).copy()
    height, width, channels = arr.shape
    if channels == 3:
        bytes_per_line = 3 * width
        return QImage(arr.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
    if channels == 4:
        bytes_per_line = 4 * width
        return QImage(arr.data, width, height, bytes_per_line, QImage.Format_RGBA8888).copy()
    raise ValueError(f'Unsupported number of channels: {channels}')
def qimage_to_numpy(qimage):
    """Convert a QImage to a NumPy array."""
    qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
    width = qimage.width()
    height = qimage.height()
    bytes_per_line = qimage.bytesPerLine()
    ptr = qimage.bits()
    ptr.setsize(height * bytes_per_line)
    arr = np.array(ptr).reshape(height, bytes_per_line)
    arr = arr[:, :width * 4].reshape(height, width, 4)
    return arr.copy()
def numpy_to_pil(arr):
    """Convert a NumPy array to a PIL Image."""
    if arr.ndim == 2:
        return Image.fromarray(arr, 'L')
    if arr.shape[2] == 3:
        return Image.fromarray(arr, 'RGB')
    if arr.shape[2] == 4:
        return Image.fromarray(arr, 'RGBA')
    raise ValueError(f'Unsupported array shape: {arr.shape}')
def pil_to_numpy(pil_image):
    """Convert a PIL Image to a NumPy array."""
    return np.array(pil_image)
def resize_image(image, max_size, keep_aspect=True, resample=Image.LANCZOS):
    """Resize an image to fit within max_size while maintaining aspect ratio."""
    if keep_aspect:
        ratio = min(max_size / image.width, max_size / image.height)
        if ratio >= 1:
            return image
        new_size = (int(image.width * ratio), int(image.height * ratio))
    else:
        new_size = (max_size, max_size)
    return image.resize(new_size, resample)
def create_thumbnail(image, size):
    """Create a thumbnail of the image."""
    thumb = image.copy()
    thumb.thumbnail(size, Image.LANCZOS)
    return thumb
def ensure_rgba(image):
    """Ensure image is in RGBA mode."""
    if image.mode != 'RGBA':
        return image.convert('RGBA')
    return image
def ensure_rgb(image, background_color=(255, 255, 255)):
    """Ensure image is in RGB mode, compositing alpha over background."""
    if image.mode == 'RGB':
        return image
    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, background_color)
        background.paste(image, mask=image.split()[3])
        return background
    return image.convert('RGB')
def get_image_info(image):
    """Get information about an image."""
    return {
        'width': image.width,
        'height': image.height,
        'mode': image.mode,
        'format': image.format,
        'size_bytes': len(image.tobytes()) if image.mode else 0,
        'has_alpha': image.mode in ('RGBA', 'LA', 'PA'),
    }
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)
def create_checkerboard(size, square_size=16, color1=(255, 255, 255), color2=(204, 204, 204)):
    """Create a checkerboard pattern image."""
    width, height = size
    rows = np.arange(height) // square_size
    cols = np.arange(width) // square_size
    checker = (rows[:, np.newaxis] + cols[np.newaxis, :]) % 2 == 0
    img_arr = np.empty((height, width, 3), dtype=np.uint8)
    img_arr[checker] = color1
    img_arr[~checker] = color2
    return Image.fromarray(img_arr, 'RGB')
