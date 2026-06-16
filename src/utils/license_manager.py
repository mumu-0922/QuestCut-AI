'''
src/utils/license_manager.py
License key verification system for QuestCut-AI.
Uses LemonSqueezy License API for activation and validation.
Handles HWID generation, remote verification, local caching, and the activation dialog.
'''
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import getnode
import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from src.utils.constants import APP_NAME, COLORS
from src.utils.i18n import tr
logger = logging.getLogger(__name__)
LEMONSQUEEZY_ACTIVATE_URL = 'https://api.lemonsqueezy.com/v1/licenses/activate'
LEMONSQUEEZY_VALIDATE_URL = 'https://api.lemonsqueezy.com/v1/licenses/validate'
_APP_DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / 'QuestCut-AI'
LICENSE_FILE = _APP_DATA_DIR / 'license.json'
def get_distribution():
    '''Determine the distribution channel for this build.
    Priority:
    1. distribution.txt file (created during build, bundled in frozen app)
    2. APP_DISTRIBUTION environment variable (for development/testing)
    3. Default to "direct" if neither exists
    '''
    if getattr(sys, 'frozen', False):
        dist_file = Path(sys._MEIPASS) / 'distribution.txt'
    else:
        dist_file = Path(__file__).resolve().parent.parent.parent / 'distribution.txt'
    if dist_file.exists():
        return dist_file.read_text().strip()
    if os.environ.get('APP_DISTRIBUTION'):
        return os.environ['APP_DISTRIBUTION'].strip()
    return 'direct'
def _get_hwid():
    '''Generate a stable, privacy-friendly hardware identifier.
    On Windows: SHA-256 of (baseboard serial + CPU processor ID).
    Fallback (non-Windows or wmic failure): SHA-256 of (hostname + MAC address).
    '''
    raw = ''
    if platform.system() == 'Windows':
        try:
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'serialnumber'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                raw += lines[1].strip()
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'processorid'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                raw += lines[1].strip()
        except Exception:
            raw = ''
    if not raw:
        raw = platform.node() + str(getnode())
    return hashlib.sha256(raw.encode()).hexdigest()
def _read_cache():
    '''Read the local license cache. Returns None on missing or corrupt file.'''
    if not LICENSE_FILE.exists():
        return None
    try:
        return json.loads(LICENSE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None
def _write_cache(license_key = None, instance_id = None, hwid = None):
    '''Write (or update) the local license cache.'''
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        'license_key': license_key,
        'instance_id': instance_id,
        'hwid': hwid,
        'activated_at': now_iso,
        'last_verified': now_iso
    }
    try:
        _APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        LICENSE_FILE.write_text(json.dumps(data, indent=2))
    except OSError:
        logger.error('Failed to write license cache.')
def _update_cache_verified():
    '''Update the last_verified timestamp in the cache.'''
    cache = _read_cache()
    if cache is None:
        return
    cache['last_verified'] = datetime.now(timezone.utc).isoformat()
    try:
        LICENSE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass
def _activate_remote(license_key=None, instance_name=None):
    '''Activate a license key via LemonSqueezy.
    Returns (success: bool, message: str, instance_id: str | None).
    '''
    try:
        resp = requests.post(
            LEMONSQUEEZY_ACTIVATE_URL,
            json={
                'license_key': license_key,
                'instance_name': instance_name
            },
            timeout=15,
            headers={'Accept': 'application/json'}
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('activated'):
            return (True, 'License activated successfully.', data.get('instance', {}).get('id'))
        else:
            error_msg = data.get('error', 'Activation failed.')
            return (False, error_msg, None)
    except requests.exceptions.ConnectionError:
        return (False, 'CONNECTION_ERROR', None)
    except Exception as e:
        return (False, str(e), None)
def _validate_remote(license_key=None, instance_id=None):
    '''Validate a license key + instance via LemonSqueezy.
    Returns (valid: bool, message: str).
    '''
    try:
        resp = requests.post(
            LEMONSQUEEZY_VALIDATE_URL,
            json={
                'license_key': license_key,
                'instance_id': instance_id
            },
            timeout=15,
            headers={'Accept': 'application/json'}
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('valid'):
            return (True, 'License is valid.')
        else:
            return (False, data.get('error', 'Validation failed.'))
    except requests.exceptions.ConnectionError:
        return (False, 'CONNECTION_ERROR')
    except Exception as e:
        return (False, str(e))
def check_license():
    '''Check whether a valid license exists.
    Once activated, the license is permanent on this machine.
    Only verifies that a cached license exists and matches this hardware.
    '''
    cache = _read_cache()
    if cache is None:
        return False
    license_key = cache.get('license_key', '')
    instance_id = cache.get('instance_id', '')
    cached_hwid = cache.get('hwid', '')
    if not license_key or not instance_id:
        return False
    hwid = _get_hwid()
    if cached_hwid and cached_hwid != hwid:
        logger.warning('HWID mismatch — cached license is for a different machine.')
        return False
    logger.info('License valid (cached, HWID matched).')
    return True
def _get_app_icon():
    '''Try to find the application icon (mirrors main.py logic).'''
    candidates = [
        Path('assets/icon.ico'),
        Path('assets/QuestCut-AI Logo.png')]
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS', '.'))
    else:
        base = Path(__file__).resolve().parent.parent.parent
    candidates += [
        base / 'assets' / 'icon.ico',
        base / 'assets' / 'QuestCut-AI Logo.png']
    for p in candidates:
        if p.exists():
            return QIcon(str(p))
    return QIcon()
class LicenseDialog(QDialog):
    '''Modal dialog for entering and activating a license key.'''
    def __init__(self, parent = None):
        super().__init__(parent)
        self._hwid = _get_hwid()
        self._setup_ui()
    def _setup_ui(self):
        self.setWindowTitle(f"{tr('Activate')} {APP_NAME}")
        self.setFixedSize(500, 350)
        self.setWindowFlags(self.windowFlags() & ~(Qt.WindowContextHelpButtonHint))
        icon = _get_app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.setStyleSheet(f'''\n            QDialog {{\n                background-color: {COLORS['bg_secondary']};\n            }}\n            QLabel {{\n                color: {COLORS['text_primary']};\n            }}\n        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(12)
        title = QLabel(f"{tr('Activate')} {APP_NAME}")
        title.setFont(QFont('Segoe UI', 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f'''color: {COLORS['accent_primary']};''')
        layout.addWidget(title)
        subtitle = QLabel(tr('Enter your license key to continue.'))
        subtitle.setFont(QFont('Segoe UI', 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f'''color: {COLORS['text_secondary']};''')
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText('xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
        self._key_input.setFont(QFont('Segoe UI', 12))
        self._key_input.setMinimumHeight(40)
        self._key_input.setStyleSheet(f'''\n            QLineEdit {{\n                border: 2px solid {COLORS['border_medium']};\n                border-radius: 6px;\n                padding: 6px 12px;\n                background: {COLORS['bg_tertiary']};\n                color: {COLORS['text_primary']};\n            }}\n            QLineEdit:focus {{\n                border-color: {COLORS['accent_primary']};\n            }}\n        ''')
        self._key_input.returnPressed.connect(self._on_activate)
        layout.addWidget(self._key_input)
        self._status_label = QLabel('')
        self._status_label.setFont(QFont('Segoe UI', 10))
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setMinimumHeight(30)
        layout.addWidget(self._status_label)
        layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self._exit_btn = QPushButton(tr('Exit'))
        self._exit_btn.setFont(QFont('Segoe UI', 11))
        self._exit_btn.setMinimumHeight(38)
        self._exit_btn.setMinimumWidth(100)
        self._exit_btn.setStyleSheet(f'''\n            QPushButton {{\n                background-color: {COLORS['bg_tertiary']};\n                color: {COLORS['text_primary']};\n                border: 1px solid {COLORS['border_medium']};\n                border-radius: 6px;\n                padding: 6px 20px;\n            }}\n            QPushButton:hover {{\n                background-color: {COLORS['bg_hover']};\n            }}\n        ''')
        self._exit_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._exit_btn)
        self._activate_btn = QPushButton(tr('Activate'))
        self._activate_btn.setFont(QFont('Segoe UI', 11, QFont.Bold))
        self._activate_btn.setMinimumHeight(38)
        self._activate_btn.setMinimumWidth(140)
        self._activate_btn.setStyleSheet(f'''\n            QPushButton {{\n                background-color: {COLORS['accent_primary']};\n                color: {COLORS['text_primary']};\n                border: none;\n                border-radius: 6px;\n                padding: 6px 20px;\n            }}\n            QPushButton:hover {{\n                background-color: {COLORS['accent_hover']};\n            }}\n            QPushButton:disabled {{\n                background-color: {COLORS['text_muted']};\n            }}\n        ''')
        self._activate_btn.clicked.connect(self._on_activate)
        btn_layout.addWidget(self._activate_btn)
        layout.addLayout(btn_layout)
    def _set_status(self, text=None, *, error=False, success=False):
        if error:
            color = COLORS['accent_error']
        elif success:
            color = COLORS['accent_success']
        else:
            color = COLORS['text_secondary']
        self._status_label.setStyleSheet(f'''color: {color};''')
        self._status_label.setText(text)
    def _on_activate(self):
        key = self._key_input.text().strip()
        if not key:
            self._set_status(tr('Please enter a license key.'), error=True)
            return None
        self._activate_btn.setEnabled(False)
        self._set_status(tr('Verifying...'))
        QApplication.processEvents()
        (ok, msg, instance_id) = _activate_remote(key, self._hwid)
        self._activate_btn.setEnabled(True)
        if ok:
            _write_cache(key, instance_id, self._hwid)
            self._set_status(tr('License activated!'), success=True)
            logger.info('License activated successfully via LemonSqueezy.')
            self.accept()
            return None
        if msg == 'CONNECTION_ERROR':
            self._set_status('Unable to reach the license server. Please check your internet connection and try again.', error=True)
            return None
        if 'limit' in msg.lower():
            self._set_status('This license key has reached its activation limit. Please deactivate another device or contact support.', error=True)
            return None
        self._set_status(msg, error=True)
