"""
Settings Presets for QuestCut-AI
=============================
Save and load user presets for background, shadow, edge, and export settings.
"""
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


@dataclass
class BackgroundPreset:
    type: str = 'transparent'
    color: str = '#ffffff'
    gradient_color1: str = '#ff7e5f'
    gradient_color2: str = '#feb47b'

    def to_dict(self):
        return asdict(self)


@dataclass
class ShadowPreset:
    enabled: bool = True
    blur: int = 25
    opacity: int = 30
    distance: int = 8

    def to_dict(self):
        return asdict(self)


@dataclass
class EdgePreset:
    sharpen: float = 0.0
    feather: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class ExportPreset:
    format: str = 'png'
    quality: int = 95

    def to_dict(self):
        return asdict(self)


@dataclass
class SettingsPreset:
    name: str = ''
    description: str = ''
    background: BackgroundPreset = field(default_factory=BackgroundPreset)
    shadow: ShadowPreset = field(default_factory=ShadowPreset)
    edge: EdgePreset = field(default_factory=EdgePreset)
    export: ExportPreset = field(default_factory=ExportPreset)

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'background': self.background.to_dict(),
            'shadow': self.shadow.to_dict(),
            'edge': self.edge.to_dict(),
            'export': self.export.to_dict(),
        }


@dataclass
class BatchPreset:
    name: str = ''
    model_key: str = ''
    export_format: str = 'png'
    quality: int = 95
    naming_template: str = '{original}'
    auto_save: bool = True
    output_dir_template: str = ''

    def to_dict(self):
        return asdict(self)


def _safe_dataclass_init(cls=None, data=None):
    """Create a dataclass instance, ignoring any extra keys not in the dataclass."""
    import dataclasses
    valid_keys = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return cls(**filtered)


class PresetManager:
    """Manages user settings presets. Stores presets using QSettings for persistence."""

    SETTINGS_KEY = 'presets'
    BATCH_SETTINGS_KEY = 'batch_presets'
    MAX_PRESETS = 20
    MAX_BATCH_PRESETS = 20

    BUILTIN_PRESETS = {
        'default': SettingsPreset(
            name='Default',
            description='Standard settings for general use',
            background=BackgroundPreset(type='transparent'),
            shadow=ShadowPreset(enabled=True, blur=25, opacity=30, distance=8),
            edge=EdgePreset(),
            export=ExportPreset(),
        ),
        'product_white': SettingsPreset(
            name='Product (White BG)',
            description='Clean white background for e-commerce',
            background=BackgroundPreset(type='solid', color='#ffffff'),
            shadow=ShadowPreset(enabled=True, blur=20, opacity=20, distance=5),
            edge=EdgePreset(sharpen=0.1),
            export=ExportPreset(format='png'),
        ),
        'social_media': SettingsPreset(
            name='Social Media',
            description='Gradient background for social posts',
            background=BackgroundPreset(type='gradient', gradient_color1='#ff7e5f', gradient_color2='#feb47b'),
            shadow=ShadowPreset(enabled=True, blur=30, opacity=40, distance=15),
            edge=EdgePreset(),
            export=ExportPreset(format='png', quality=90),
        ),
        'portrait': SettingsPreset(
            name='Portrait',
            description='Optimized for portraits',
            background=BackgroundPreset(type='transparent'),
            shadow=ShadowPreset(enabled=False),
            edge=EdgePreset(feather=2, sharpen=-0.2),
            export=ExportPreset(format='png'),
        ),
        'dramatic': SettingsPreset(
            name='Dramatic Shadow',
            description='Bold shadow effect',
            background=BackgroundPreset(type='transparent'),
            shadow=ShadowPreset(enabled=True, blur=30, opacity=70, distance=20),
            edge=EdgePreset(sharpen=0.2),
            export=ExportPreset(format='png'),
        ),
    }

    BUILTIN_NAMES = [p.name for p in BUILTIN_PRESETS.values()]

    def __init__(self):
        self._settings = QSettings('QuestCut', 'QuestCut-AI')
        self._presets = {}
        self._batch_presets = {}
        self._load_presets()
        self._load_batch_presets()

    def _load_presets(self):
        """Load presets from settings."""
        data = self._settings.value(self.SETTINGS_KEY, '{}')
        try:
            raw = json.loads(data)
            for name, pdata in raw.items():
                try:
                    preset = SettingsPreset(
                        name=pdata.get('name', name),
                        description=pdata.get('description', ''),
                        background=_safe_dataclass_init(BackgroundPreset, pdata.get('background', {})),
                        shadow=_safe_dataclass_init(ShadowPreset, pdata.get('shadow', {})),
                        edge=_safe_dataclass_init(EdgePreset, pdata.get('edge', {})),
                        export=_safe_dataclass_init(ExportPreset, pdata.get('export', {})),
                    )
                    self._presets[name] = preset
                except Exception:
                    logger.warning(f'Failed to load preset: {name}')
        except (json.JSONDecodeError, TypeError):
            pass

    def _save_presets(self):
        """Save presets to settings."""
        presets_dict = {k: v.to_dict() for k, v in self._presets.items()}
        self._settings.setValue(self.SETTINGS_KEY, json.dumps(presets_dict))
        self._settings.sync()

    def get_preset(self, name=None):
        """Get a preset by name. Checks user presets first, then built-in."""
        if name in self._presets:
            return self._presets[name]
        if name in self.BUILTIN_PRESETS:
            return self.BUILTIN_PRESETS[name]
        return None

    def get_all_presets(self):
        """Get all presets (built-in and user)."""
        all_presets = dict(self.BUILTIN_PRESETS)
        all_presets.update(self._presets)
        return all_presets

    def get_user_presets(self):
        """Get only user-created presets."""
        return self._presets.copy()

    def get_builtin_presets(self):
        """Get only built-in presets."""
        return dict(self.BUILTIN_PRESETS)

    def save_preset(self, preset=None):
        """Save a preset. Returns True if saved successfully."""
        if preset.name in self.BUILTIN_NAMES:
            logger.warning(f'Cannot overwrite built-in preset: {preset.name}')
            return False
        if len(self._presets) >= self.MAX_PRESETS and preset.name not in self._presets:
            logger.warning('Maximum preset limit reached')
            return False
        self._presets[preset.name] = preset
        self._save_presets()
        logger.info(f'Saved preset: {preset.name}')
        return True

    def delete_preset(self, name=None):
        """Delete a user preset. Returns True if deleted."""
        if name in self.BUILTIN_NAMES:
            logger.warning(f'Cannot delete built-in preset: {name}')
            return False
        if name in self._presets:
            del self._presets[name]
            self._save_presets()
            logger.info(f'Deleted preset: {name}')
            return True
        return False

    def rename_preset(self, old_name=None, new_name=None):
        """Rename a user preset. Returns True if renamed."""
        if old_name in self.BUILTIN_NAMES:
            logger.warning(f'Cannot rename built-in preset: {old_name}')
            return False
        if old_name not in self._presets:
            return False
        if new_name in self._presets or new_name in self.BUILTIN_NAMES:
            logger.warning(f'Preset name already exists: {new_name}')
            return False
        preset = self._presets.pop(old_name)
        preset.name = new_name
        self._presets[new_name] = preset
        self._save_presets()
        logger.info(f'Renamed preset: {old_name} -> {new_name}')
        return True

    def export_preset(self, name=None, file_path=None):
        """Export a preset to JSON file."""
        preset = self.get_preset(name)
        if not preset:
            return False
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(preset.to_dict(), f, indent=2)
        logger.info(f'Exported preset to: {file_path}')
        return True

    def import_preset(self, file_path=None):
        """Import a preset from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            preset = _safe_dataclass_init(SettingsPreset, data)
            preset.background = _safe_dataclass_init(BackgroundPreset, data.get('background', {}))
            preset.shadow = _safe_dataclass_init(ShadowPreset, data.get('shadow', {}))
            preset.edge = _safe_dataclass_init(EdgePreset, data.get('edge', {}))
            preset.export = _safe_dataclass_init(ExportPreset, data.get('export', {}))
            return self.save_preset(preset)
        except Exception as e:
            logger.error(f'Failed to import preset: {e}')
            return False

    def get_preset_names(self):
        """Get list of all preset names."""
        names = list(self.BUILTIN_PRESETS.keys())
        names.extend(self._presets.keys())
        return names

    def is_builtin(self, name=None):
        """Check if a preset is built-in."""
        return name in self.BUILTIN_NAMES

    def _load_batch_presets(self):
        """Load batch presets from settings."""
        data = self._settings.value(self.BATCH_SETTINGS_KEY, '{}')
        try:
            raw = json.loads(data)
            for name, pdata in raw.items():
                try:
                    preset = _safe_dataclass_init(BatchPreset, pdata)
                    self._batch_presets[name] = preset
                except Exception:
                    logger.warning(f'Failed to load batch preset: {name}')
        except (json.JSONDecodeError, TypeError):
            pass

    def _save_batch_presets(self):
        """Save batch presets to settings."""
        presets_dict = {k: v.to_dict() for k, v in self._batch_presets.items()}
        self._settings.setValue(self.BATCH_SETTINGS_KEY, json.dumps(presets_dict))
        self._settings.sync()

    def get_batch_preset(self, name=None):
        """Get a batch preset by name."""
        return self._batch_presets.get(name)

    def get_all_batch_presets(self):
        """Get all batch presets."""
        return self._batch_presets.copy()

    def save_batch_preset(self, preset=None):
        """Save a batch preset."""
        if len(self._batch_presets) >= self.MAX_BATCH_PRESETS and preset.name not in self._batch_presets:
            logger.warning('Maximum batch preset limit reached')
            return False
        self._batch_presets[preset.name] = preset
        self._save_batch_presets()
        logger.info(f'Saved batch preset: {preset.name}')
        return True

    def delete_batch_preset(self, name=None):
        """Delete a batch preset."""
        if name in self._batch_presets:
            del self._batch_presets[name]
            self._save_batch_presets()
            logger.info(f'Deleted batch preset: {name}')
            return True
        return False


_preset_manager: Optional[PresetManager] = None


def get_preset_manager():
    """Get the global preset manager."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager
