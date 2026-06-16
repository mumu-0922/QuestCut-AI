"""
Icons for QuestCut-AI
=================
SVG icons for toolbar and UI elements.
"""
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import QByteArray, QBuffer, QSize, Qt
from PySide6.QtSvg import QSvgRenderer
from typing import Dict, Optional

# Minimal SVG icon set for toolbar actions
ICONS_SVG = {
    'open': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M19 20H5c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2h4l2 2h8c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2z"/></svg>',
    'save': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M17 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg>',
    'undo': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>',
    'redo': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/></svg>',
    'brush': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M7 14c-1.66 0-3 1.34-3 3 0 1.31-1.16 2-2 2 .92 1.22 2.49 2 4 2 2.21 0 4-1.79 4-4 0-1.66-1.34-3-3-3zm13.71-9.37l-1.34-1.34c-.39-.39-1.02-.39-1.41 0L9 12.25 11.75 15l8.96-8.96c.39-.39.39-1.02 0-1.41z"/></svg>',
    'eraser': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M16.24 3.56l4.95 4.94c.78.79.78 2.05 0 2.84L12 20.53a4.01 4.01 0 01-5.66 0L2.81 17c-.78-.79-.78-2.05 0-2.84l10.6-10.6c.79-.78 2.05-.78 2.83 0zM4.22 15.58l3.54 3.54c.78.78 2.05.78 2.83 0l3.54-3.54-6.37-6.37-3.54 6.37z"/></svg>',
    'zoom_in': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zm.5-2h2v-2h2V8h-2V6h-2v2h-2v2h2v2z"/></svg>',
    'zoom_out': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zm-3-5h6v2h-6V9z"/></svg>',
    'fit': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M3 5v4h2V5h4V3H5c-1.1 0-2 .9-2 2zm2 10H3v4c0 1.1.9 2 2 2h4v-2H5v-4zm14 4h-4v2h4c1.1 0 2-.9 2-2v-4h-2v4zm0-16h-4v2h4v4h2V5c0-1.1-.9-2-2-2z"/></svg>',
    'comparison': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M9 3L5 6.99h3V14h2V6.99h3L9 3zm7 14.01V10h-2v7.01h-3L15 21l4-3.99h-3z"/></svg>',
    'process': '<svg viewBox="0 0 24 24"><circle fill="none" stroke="#a0a0a5" stroke-width="2" cx="12" cy="12" r="10"/><polygon fill="#a0a0a5" points="10,8 16,12 10,16"/></svg>',
    'batch': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>',
    'settings': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.63-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>',
    'shadow': '<svg viewBox="0 0 24 24"><circle fill="#a0a0a5" opacity=".3" cx="12" cy="12" r="10"/><circle fill="none" stroke="#a0a0a5" stroke-width="2" cx="12" cy="10" r="8"/></svg>',
    'background': '<svg viewBox="0 0 24 24"><rect fill="#a0a0a5" opacity=".3" x="2" y="2" width="20" height="20" rx="2"/><rect fill="none" stroke="#a0a0a5" stroke-width="2" x="2" y="2" width="20" height="20" rx="2"/></svg>',
    'export': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>',
    'info': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>',
    'license': '<svg viewBox="0 0 24 24"><path fill="#a0a0a5" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>',
    'remove': '<svg viewBox="0 0 24 24"><circle fill="#ef4444" cx="12" cy="12" r="10"/><path fill="#fff" d="M15.5 9.5l-1-1-2.5 2.5-2.5-2.5-1 1 2.5 2.5-2.5 2.5 1 1 2.5-2.5 2.5 2.5 1-1-2.5-2.5z"/></svg>',
    'add': '<svg viewBox="0 0 24 24"><circle fill="#22c55e" cx="12" cy="12" r="10"/><path fill="#fff" d="M11 11H8v2h3v3h2v-3h3v-2h-3V8h-2v3z"/></svg>',
}


class IconManager:
    """Manages application icons using SVG rendering."""

    def __init__(self):
        self._icons: Dict[str, QIcon] = {}
        self._pixmaps: Dict[str, QPixmap] = {}
        self._build_icons()

    def _svg_to_icon(self, svg_data: str) -> QIcon:
        """Convert SVG string to QIcon."""
        renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def _build_icons(self):
        """Build all icons from SVG data."""
        for name, svg in ICONS_SVG.items():
            icon = self._svg_to_icon(svg)
            self._icons[name] = icon
            self._pixmaps[name] = icon.pixmap(24, 24)

    def get_icon(self, name: str, size: int = 24) -> QIcon:
        """Get an icon by name. Returns empty icon if not found."""
        return self._icons.get(name, QIcon())

    def get_pixmap(self, name: str, size: int = 24) -> QPixmap:
        """Get a pixmap by name."""
        icon = self.get_icon(name)
        return icon.pixmap(size, size)

    def get_all_names(self):
        """Return list of all icon names."""
        return list(self._icons.keys())


_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """Get the global icon manager singleton."""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager


def get_icon(name: str, size: int = 24) -> QIcon:
    """Get an icon by name from the global manager."""
    return get_icon_manager().get_icon(name, size)


def get_pixmap(name: str, size: int = 24) -> QPixmap:
    """Get a pixmap by name from the global manager."""
    return get_icon_manager().get_pixmap(name, size)
