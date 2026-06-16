"""
Settings Manager for QuestCut-AI
=============================
Handles persistent storage of user preferences using QSettings.
"""
from typing import Any, Optional, Dict
from PySide6.QtCore import QSettings
from .constants import DEFAULT_SETTINGS
class Settings:
    """
    Settings manager for persistent user preferences.
    Uses QSettings for cross-platform storage:
    - Windows: Registry
    - macOS: plist files
    - Linux: INI files
    """
    def __init__(self, organization=None, application=None):
        self._settings = QSettings(organization, application)
        self._defaults = DEFAULT_SETTINGS.copy()
    def get(self, key, default=None):
        if default is None:
            default = self._defaults.get(key)
        value = self._settings.value(key, default)
        if isinstance(default, bool):
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        return value
    def set(self, key, value):
        self._settings.setValue(key, value)
    def remove(self, key):
        self._settings.remove(key)
    def contains(self, key):
        return self._settings.contains(key)
    def clear(self):
        self._settings.clear()
    def sync(self):
        self._settings.sync()
    def all_keys(self):
        return self._settings.allKeys()
    def get_all(self):
        result = {}
        for key in self._settings.allKeys():
            result[key] = self._settings.value(key)
        return result
    def set_defaults(self, defaults):
        self._defaults.update(defaults)
    def reset_to_defaults(self):
        self._settings.clear()
        for key, value in self._defaults.items():
            self._settings.setValue(key, value)
    @property
    def default_model(self):
        return self.get('default_model', 'birefnet')
    @default_model.setter
    def default_model(self, value):
        self.set('default_model', value)
    @property
    def use_gpu(self):
        return self.get('use_gpu', True)
    @use_gpu.setter
    def use_gpu(self, value):
        self.set('use_gpu', value)
    @property
    def default_format(self):
        return self.get('default_format', 'png')
    @default_format.setter
    def default_format(self, value):
        self.set('default_format', value)
    @property
    def default_quality(self):
        return self.get('default_quality', 90)
    @default_quality.setter
    def default_quality(self, value):
        self.set('default_quality', value)
    @property
    def filename_template(self):
        return self.get('filename_template', '{original}_nobg')
    @filename_template.setter
    def filename_template(self, value):
        self.set('filename_template', value)
_settings_instance: Optional[Settings] = None
def get_settings():
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
