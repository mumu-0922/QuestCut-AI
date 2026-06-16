"""
Constants and Presets for QuestCut-AI
=================================
All configuration values, presets, and constants used throughout the application.
"""
from typing import Dict, Any
APP_NAME = 'QuestCut-AI'
APP_VERSION = '1.0.1'
APP_AUTHOR = 'QuestCut'
APP_WEBSITE = 'https://github.com/QuestCut-AI/QuestCut-AI'
COLORS = {
    'bg_primary': '#0f0f10',
    'bg_secondary': '#1a1a1d',
    'bg_tertiary': '#2a2a2f',
    'bg_hover': '#3a3a40',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a5',
    'text_muted': '#606065',
    'accent_primary': '#4F46E5',
    'accent_hover': '#4338CA',
    'accent_success': '#22c55e',
    'accent_warning': '#f59e0b',
    'accent_error': '#ef4444',
    'border_light': '#2a2a2f',
    'border_medium': '#3a3a40',
    'border_dark': '#1a1a1d',
    'transparent_checker_light': '#ffffff',
    'transparent_checker_dark': '#cccccc',
}
GRADIENT_PRESETS = {
    'sunset': {'name': 'Sunset', 'color1': '#ff7e5f', 'color2': '#feb47b', 'direction': 135},
    'ocean': {'name': 'Ocean', 'color1': '#2193b0', 'color2': '#6dd5ed', 'direction': 135},
    'forest': {'name': 'Forest', 'color1': '#134e5e', 'color2': '#71b280', 'direction': 135},
    'purple_haze': {'name': 'Purple Haze', 'color1': '#7f00ff', 'color2': '#e100ff', 'direction': 135},
    'midnight': {'name': 'Midnight', 'color1': '#232526', 'color2': '#414345', 'direction': 180},
    'golden_hour': {'name': 'Golden Hour', 'color1': '#f5af19', 'color2': '#f12711', 'direction': 135},
    'cool_gray': {'name': 'Cool Gray', 'color1': '#bdc3c7', 'color2': '#2c3e50', 'direction': 180},
    'warmth': {'name': 'Warmth', 'color1': '#ffecd2', 'color2': '#fcb69f', 'direction': 135},
    'mint': {'name': 'Mint', 'color1': '#a8e6cf', 'color2': '#88d8b0', 'direction': 135},
    'lavender': {'name': 'Lavender', 'color1': '#e0c3fc', 'color2': '#8ec5fc', 'direction': 135},
    'peach': {'name': 'Peach', 'color1': '#ffdab9', 'color2': '#ff9a76', 'direction': 180},
    'slate': {'name': 'Slate', 'color1': '#4b6cb7', 'color2': '#182848', 'direction': 180},
}
SHADOW_PRESETS = {
    'none': {'name': 'None', 'enabled': False, 'blur': 0, 'opacity': 0, 'distance': 0, 'angle': 135, 'color': '#000000'},
    'soft': {'name': 'Soft', 'enabled': True, 'blur': 25, 'opacity': 30, 'distance': 8, 'angle': 135, 'color': '#000000'},
    'hard': {'name': 'Hard', 'enabled': True, 'blur': 5, 'opacity': 60, 'distance': 5, 'angle': 135, 'color': '#000000'},
    'floating': {'name': 'Floating', 'enabled': True, 'blur': 40, 'opacity': 40, 'distance': 25, 'angle': 180, 'color': '#000000'},
    'grounded': {'name': 'Grounded', 'enabled': True, 'blur': 15, 'opacity': 50, 'distance': 0, 'angle': 180, 'color': '#000000'},
    'dramatic': {'name': 'Dramatic', 'enabled': True, 'blur': 30, 'opacity': 70, 'distance': 20, 'angle': 135, 'color': '#000000'},
    'subtle': {'name': 'Subtle', 'enabled': True, 'blur': 15, 'opacity': 20, 'distance': 5, 'angle': 135, 'color': '#000000'},
}
PLATFORM_SIZES = {
    'amazon_main': {'width': 2000, 'height': 2000, 'name': 'Amazon (2000)', 'folder': 'E-Commerce', 'aspect': '1:1', 'category': 'e-commerce'},
    'amazon_square': {'width': 1600, 'height': 1600, 'name': 'Amazon (1600)', 'folder': 'E-Commerce', 'aspect': '1:1', 'category': 'e-commerce'},
    'shopify': {'width': 2048, 'height': 2048, 'name': 'Shopify', 'folder': 'E-Commerce', 'aspect': '1:1', 'category': 'e-commerce'},
    'etsy': {'width': 2000, 'height': 1500, 'name': 'Etsy', 'folder': 'E-Commerce', 'aspect': '4:3', 'category': 'e-commerce'},
    'ebay': {'width': 1600, 'height': 1600, 'name': 'eBay', 'folder': 'E-Commerce', 'aspect': '1:1', 'category': 'e-commerce'},
    'sprite_64': {'width': 64, 'height': 64, 'name': '64 x 64', 'folder': 'Sprites', 'aspect': '1:1', 'category': 'game'},
    'sprite_128': {'width': 128, 'height': 128, 'name': '128 x 128', 'folder': 'Sprites', 'aspect': '1:1', 'category': 'game'},
    'sprite_256': {'width': 256, 'height': 256, 'name': '256 x 256', 'folder': 'Sprites', 'aspect': '1:1', 'category': 'game'},
    'sprite_512': {'width': 512, 'height': 512, 'name': '512 x 512', 'folder': 'Sprites', 'aspect': '1:1', 'category': 'game'},
    'sprite_1024': {'width': 1024, 'height': 1024, 'name': '1024 x 1024', 'folder': 'Sprites', 'aspect': '1:1', 'category': 'game'},
    'instagram_square': {'width': 1080, 'height': 1080, 'name': 'Instagram Square', 'folder': 'Instagram', 'aspect': '1:1', 'category': 'social'},
    'instagram_portrait': {'width': 1080, 'height': 1350, 'name': 'Instagram Portrait', 'folder': 'Instagram', 'aspect': '4:5', 'category': 'social'},
    'instagram_story': {'width': 1080, 'height': 1920, 'name': 'Instagram Story', 'folder': 'Instagram', 'aspect': '9:16', 'category': 'social'},
    'facebook_post': {'width': 1200, 'height': 630, 'name': 'Facebook Post', 'folder': 'Facebook', 'aspect': '1.91:1', 'category': 'social'},
    'facebook_cover': {'width': 820, 'height': 312, 'name': 'Facebook Cover', 'folder': 'Facebook', 'aspect': '2.63:1', 'category': 'social'},
    'tiktok': {'width': 1080, 'height': 1920, 'name': 'TikTok', 'folder': 'TikTok', 'aspect': '9:16', 'category': 'social'},
    'twitter': {'width': 1200, 'height': 675, 'name': 'Twitter/X', 'folder': 'Twitter', 'aspect': '16:9', 'category': 'social'},
    'pinterest': {'width': 1000, 'height': 1500, 'name': 'Pinterest', 'folder': 'Pinterest', 'aspect': '2:3', 'category': 'social'},
    'linkedin': {'width': 1200, 'height': 627, 'name': 'LinkedIn', 'folder': 'LinkedIn', 'aspect': '1.91:1', 'category': 'social'},
    'youtube_thumbnail': {'width': 1280, 'height': 720, 'name': 'YouTube Thumbnail', 'folder': 'YouTube', 'aspect': '16:9', 'category': 'social'},
    'website_hero': {'width': 1920, 'height': 1080, 'name': 'Website Hero', 'folder': 'Website', 'aspect': '16:9', 'category': 'web'},
    'website_square': {'width': 800, 'height': 800, 'name': 'Website Square', 'folder': 'Website', 'aspect': '1:1', 'category': 'web'},
}
PLATFORM_CATEGORIES = {
    'e-commerce': 'E-Commerce / Product',
    'game': 'Game / Sprites',
    'social': 'Social Media',
    'web': 'Web',
}
MODEL_CONFIG = {
    'birefnet': {
        'name': 'BiRefNet',
        'display_name': 'BiRefNet (Best Quality)',
        'rembg_model': 'birefnet-general',
        'description': 'Highest quality segmentation for products and complex edges',
        'size': '~928MiB',
        'category': 'quality',
        'recommended_for': ['products', 'e-commerce', 'detailed edges'],
    },
    'birefnet_portrait': {
        'name': 'BiRefNet Portrait',
        'display_name': 'BiRefNet Portrait (People)',
        'rembg_model': 'birefnet-portrait',
        'description': 'Clean cutouts of people - for soft hair use Portrait Mode (MODNet)',
        'size': '~928MiB',
        'category': 'specialized',
        'recommended_for': ['full body', 'people on busy backgrounds', 'silhouettes'],
    },
    'modnet': {
        'name': 'MODNet',
        'display_name': 'Portrait Mode',
        'url': 'https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx',
        'filename': 'modnet.onnx',
        'description': 'Alpha matting for portraits - preserves fine hair and soft edges',
        'size': '~25MiB',
        'category': 'specialized',
    },
}
MODEL_DISPLAY_ORDER = ['birefnet', 'birefnet_portrait', 'modnet']
EXPORT_FORMATS = {
    'png': {
        'name': 'PNG',
        'extension': '.png',
        'mime_type': 'image/png',
        'supports_transparency': True,
        'supports_quality': False,
    },
    'jpg': {
        'name': 'JPEG',
        'extension': '.jpg',
        'mime_type': 'image/jpeg',
        'supports_transparency': False,
        'supports_quality': True,
        'default_quality': 90,
    },
    'webp': {
        'name': 'WebP',
        'extension': '.webp',
        'mime_type': 'image/webp',
        'supports_transparency': True,
        'supports_quality': True,
        'default_quality': 90,
    },
}
RESOLUTION_PRESETS = {
    '0.5x': 0.5,
    '1x': 1.0,
    '1.5x': 1.5,
    '2x': 2.0,
}
KEYBOARD_SHORTCUTS = {
    'open_file': 'Ctrl+O',
    'save_file': 'Ctrl+S',
    'save_as': 'Ctrl+Shift+S',
    'undo': 'Ctrl+Z',
    'redo': 'Ctrl+Y',
    'redo_alt': 'Ctrl+Shift+Z',
    'toggle_view': 'Space',
    'decrease_tolerance': '[',
    'increase_tolerance': ']',
    'cancel': 'Escape',
    'help': '?',
    'zoom_in': 'Ctrl+=',
    'zoom_out': 'Ctrl+-',
    'zoom_fit': 'Ctrl+0',
    'zoom_100': 'Ctrl+1',
}
DEFAULT_SETTINGS = {
    'default_model': 'birefnet',
    'auto_process': False,
    'default_background': 'transparent',
    'default_gradient': 'ocean',
    'default_shadow': 'soft',
    'default_format': 'png',
    'default_quality': 90,
    'default_resolution': 1.0,
    'filename_template': '{original}_nobg',
    'show_comparison_slider': True,
    'dark_mode': True,
    'panel_collapsed': {},
    'use_gpu': True,
    'preview_size': 1024,
    'thumbnail_size': 100,
}
IMAGE_FILTER = 'Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif)'
ALL_FILES_FILTER = 'All Files (*)'
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.gif')
