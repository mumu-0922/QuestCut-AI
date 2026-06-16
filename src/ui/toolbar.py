'''
Toolbar for QuestCut-AI
===================
Mode selection and tool buttons.
'''
import logging
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup, QLabel, QFrame, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon
from ..resources.icons import get_icon
from ..utils.i18n import tr
logger = logging.getLogger(__name__)
class ToolButton(QPushButton):
    '''Custom tool button with consistent styling.'''
    def __init__(self, text = None, icon_name = None, fallback_text = None, parent = None):
        super().__init__(parent)
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setProperty('class', 'tool-button')
        self.setFocusPolicy(Qt.StrongFocus)
class ModeButton(QPushButton):
    '''Mode selection button with description.'''
    def __init__(self, text = None, description = None, shortcut = None, parent = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setProperty('class', 'mode-button')
        self.setFocusPolicy(Qt.StrongFocus)
        tooltip = f'''<b>{text}</b>'''
        if description:
            tooltip += f'''<br><span style=\'color: #a0a0a5;\'>{description}</span>'''
        if shortcut:
            tooltip += f'''<br><span style=\'color: #4F46E5;\'>{tr('Shortcut:')} {shortcut}</span>'''
        self.setToolTip(tooltip)
        self.setAccessibleName(text)
        if description:
            self.setAccessibleDescription(description)
            return None
class Toolbar(QWidget):
    '''
    Vertical toolbar for mode and tool selection.
    Sections:
    - File operations (open, save)
    - Tools (brush add/remove)
    - Undo/Redo
    '''
    tool_changed = Signal(str, bool)
    open_clicked = Signal()
    save_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self._current_tool = 'none'
        self._is_remove_mode = False
        self._setup_ui()
        self._connect_signals()
    def _setup_ui(self):
        '''Setup the toolbar UI.'''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)
        self.file_label = QLabel(tr('File'))
        self.file_label.setProperty('class', 'section-label')
        layout.addWidget(self.file_label)
        self.open_btn = ToolButton(icon_name='open', fallback_text='Open')
        self.open_btn.setToolTip(tr('Open Image (Ctrl+O)'))
        self.open_btn.setCheckable(False)
        layout.addWidget(self.open_btn)
        self.save_btn = ToolButton(icon_name='save', fallback_text='Save')
        self.save_btn.setToolTip(tr('Save Image (Ctrl+S)'))
        self.save_btn.setCheckable(False)
        layout.addWidget(self.save_btn)
        layout.addWidget(self._create_separator())
        self.tools_label = QLabel(tr('Tools'))
        self.tools_label.setProperty('class', 'section-label')
        layout.addWidget(self.tools_label)
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self.brush_add_btn = ToolButton(icon_name='brush_add', fallback_text='+')
        self.brush_add_btn.setToolTip(f"<b>{tr('Add to Mask')}</b><br><span style='color: #a0a0a5;'>{tr('Paint to keep areas visible')}</span><br><span style='color: #4F46E5;'>{tr('[ ] to resize brush')}</span>")
        self._tool_group.addButton(self.brush_add_btn)
        layout.addWidget(self.brush_add_btn)
        self.brush_remove_btn = ToolButton(icon_name='brush_remove', fallback_text='-')
        self.brush_remove_btn.setToolTip(f"<b>{tr('Remove from Mask')}</b><br><span style='color: #a0a0a5;'>{tr('Paint to remove areas')}</span><br><span style='color: #4F46E5;'>{tr('[ ] to resize brush')}</span>")
        self._tool_group.addButton(self.brush_remove_btn)
        layout.addWidget(self.brush_remove_btn)
        self.pan_btn = ToolButton(icon_name='pan', fallback_text='Pan')
        self.pan_btn.setToolTip(f"<b>{tr('Pan View')}</b><br><span style='color: #a0a0a5;'>{tr('Drag to move around')}</span><br><span style='color: #4F46E5;'>{tr('Hold Space + drag')}</span>")
        self._tool_group.addButton(self.pan_btn)
        layout.addWidget(self.pan_btn)
        layout.addWidget(self._create_separator())
        self.edit_label = QLabel(tr('Edit'))
        self.edit_label.setProperty('class', 'section-label')
        layout.addWidget(self.edit_label)
        self.undo_btn = ToolButton(icon_name='undo', fallback_text='Un')
        self.undo_btn.setToolTip(tr('Undo (Ctrl+Z)'))
        self.undo_btn.setCheckable(False)
        layout.addWidget(self.undo_btn)
        self.redo_btn = ToolButton(icon_name='redo', fallback_text='Re')
        self.redo_btn.setToolTip(tr('Redo (Ctrl+Y)'))
        self.redo_btn.setCheckable(False)
        layout.addWidget(self.redo_btn)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.setFixedWidth(60)
    def retranslate_ui(self):
        '''Refresh language-dependent labels and tooltips.'''
        self.file_label.setText(tr('File'))
        self.tools_label.setText(tr('Tools'))
        self.edit_label.setText(tr('Edit'))
        self.open_btn.setToolTip(tr('Open Image (Ctrl+O)'))
        self.save_btn.setToolTip(tr('Save Image (Ctrl+S)'))
        self.brush_add_btn.setToolTip(f"<b>{tr('Add to Mask')}</b><br><span style='color: #a0a0a5;'>{tr('Paint to keep areas visible')}</span><br><span style='color: #4F46E5;'>{tr('[ ] to resize brush')}</span>")
        self.brush_remove_btn.setToolTip(f"<b>{tr('Remove from Mask')}</b><br><span style='color: #a0a0a5;'>{tr('Paint to remove areas')}</span><br><span style='color: #4F46E5;'>{tr('[ ] to resize brush')}</span>")
        self.pan_btn.setToolTip(f"<b>{tr('Pan View')}</b><br><span style='color: #a0a0a5;'>{tr('Drag to move around')}</span><br><span style='color: #4F46E5;'>{tr('Hold Space + drag')}</span>")
        self.undo_btn.setToolTip(tr('Undo (Ctrl+Z)'))
        self.redo_btn.setToolTip(tr('Redo (Ctrl+Y)'))
    def _create_separator(self):
        '''Create a horizontal separator line.'''
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setProperty('class', 'separator')
        return line
    def _connect_signals(self):
        '''Connect internal signals.'''
        self.open_btn.clicked.connect(self.open_clicked.emit)
        self.save_btn.clicked.connect(self.save_clicked.emit)
        self.brush_add_btn.clicked.connect(lambda: self._set_tool('brush', False))
        self.brush_remove_btn.clicked.connect(lambda: self._set_tool('brush', True))
        self.pan_btn.clicked.connect(lambda: self._set_tool('pan'))
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.redo_btn.clicked.connect(self.redo_clicked.emit)
    def _set_tool(self, tool = None, is_remove = None):
        '''Set current tool.'''
        self._current_tool = tool
        self._is_remove_mode = is_remove
        self.tool_changed.emit(tool, self._is_remove_mode)
    @property
    def current_tool(self):
        """Get current tool."""
        return self._current_tool

    @property
    def is_remove_mode(self):
        """Check if in remove/subtract mode."""
        return self._is_remove_mode
    def set_undo_enabled(self, enabled = None):
        '''Set undo button enabled state.'''
        self.undo_btn.setEnabled(enabled)
    def set_redo_enabled(self, enabled = None):
        '''Set redo button enabled state.'''
        self.redo_btn.setEnabled(enabled)
