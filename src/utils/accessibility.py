'''
Accessibility Helpers for QuestCut-AI
==================================
Functions to add ARIA-like accessibility to Qt widgets.
'''
import logging
from typing import Optional, List, Tuple
from PySide6.QtWidgets import QWidget, QPushButton, QSlider, QComboBox, QCheckBox, QSpinBox, QLineEdit, QLabel, QGroupBox
from PySide6.QtCore import Qt
logger = logging.getLogger(__name__)
def set_accessible_info(widget = None, name = None, description = None, role_hint = (None, None)):
    '''
    Set accessibility information on a widget.
    Args:
        widget: The Qt widget
        name: Accessible name (short, like a label)
        description: Accessible description (longer explanation)
        role_hint: Optional role hint added to description
    '''
    widget.setAccessibleName(name)
    if description:
        if role_hint:
            description = f'''{role_hint}. {description}'''
        widget.setAccessibleDescription(description)
        return None
    elif role_hint:
        widget.setAccessibleDescription(role_hint)
        return None
def setup_button_accessibility(button = None, name = None, description = None, shortcut = (None, None)):
    '''
    Set up accessibility for a button.
    Args:
        button: The button widget
        name: Accessible name
        description: What the button does
        shortcut: Keyboard shortcut if any
    '''
    if not description:
        pass
    full_desc = f'''Activate to {name.lower()}'''
    if shortcut:
        full_desc += f'''. Keyboard shortcut: {shortcut}'''
    set_accessible_info(button, name, full_desc, 'Button')
    button.setFocusPolicy(Qt.StrongFocus)
def setup_slider_accessibility(slider, name = None, min_val = None, max_val = None, unit = ('', None), description = ('slider', QSlider, 'name', str, 'min_val', int, 'max_val', int, 'unit', str, 'description', Optional[str])):
    '''
    Set up accessibility for a slider.
    Args:
        slider: The slider widget
        name: Accessible name (e.g., "Shadow Blur")
        min_val: Minimum value
        max_val: Maximum value
        unit: Unit string (e.g., "px", "%")
        description: Additional description
    '''
    desc = f'''Adjust {name.lower()} from {min_val} to {max_val}{unit}'''
    if description:
        desc += f'''. {description}'''
    desc += '. Use arrow keys to adjust.'
    set_accessible_info(slider, name, desc, 'Slider')
    slider.setFocusPolicy(Qt.StrongFocus)
def setup_combobox_accessibility(combo = None, name = None, description = None):
    '''
    Set up accessibility for a combo box.
    Args:
        combo: The combo box widget
        name: Accessible name
        description: What the selection controls
    '''
    if not description:
        pass
    desc = f'''Select {name.lower()}'''
    desc += '. Use arrow keys to change selection.'
    set_accessible_info(combo, name, desc, 'Dropdown list')
    combo.setFocusPolicy(Qt.StrongFocus)
def setup_checkbox_accessibility(checkbox = None, name = None, description = None):
    '''
    Set up accessibility for a checkbox.
    Args:
        checkbox: The checkbox widget
        name: Accessible name
        description: What enabling/disabling does
    '''
    if not description:
        pass
    desc = f'''Toggle {name.lower()}'''
    desc += '. Press Space to toggle.'
    set_accessible_info(checkbox, name, desc, 'Checkbox')
    checkbox.setFocusPolicy(Qt.StrongFocus)
def setup_spinbox_accessibility(spinbox, name = None, min_val = None, max_val = None, unit = ('', None), description = ('spinbox', QSpinBox, 'name', str, 'min_val', int, 'max_val', int, 'unit', str, 'description', Optional[str])):
    '''
    Set up accessibility for a spin box.
    Args:
        spinbox: The spin box widget
        name: Accessible name
        min_val: Minimum value
        max_val: Maximum value
        unit: Unit string
        description: Additional description
    '''
    desc = f'''Enter {name.lower()} between {min_val} and {max_val}{unit}'''
    if description:
        desc += f'''. {description}'''
    desc += '. Use arrow keys or type a value.'
    set_accessible_info(spinbox, name, desc, 'Number input')
    spinbox.setFocusPolicy(Qt.StrongFocus)
def setup_lineedit_accessibility(lineedit = None, name = None, placeholder = None, description = (None, None)):
    '''
    Set up accessibility for a line edit.
    Args:
        lineedit: The line edit widget
        name: Accessible name
        placeholder: Placeholder text
        description: Additional description
    '''
    if not description:
        pass
    desc = f'''Enter {name.lower()}'''
    if placeholder:
        lineedit.setPlaceholderText(placeholder)
        desc += f'''. Example: {placeholder}'''
    set_accessible_info(lineedit, name, desc, 'Text input')
    lineedit.setFocusPolicy(Qt.StrongFocus)
def setup_focus_order(widgets = None):
    '''
    Set up tab order for a list of widgets.
    Args:
        widgets: List of widgets in desired tab order
    '''
    for i in range(len(widgets) - 1):
        QWidget.setTabOrder(widgets[i], widgets[i + 1])
def setup_group_accessibility(group = None, name = None, description = None):
    '''
    Set up accessibility for a group box.
    Args:
        group: The group box widget
        name: Accessible name for the group
        description: Description of what the group contains
    '''
    if not description:
        pass
    desc = f'''{name} settings'''
    set_accessible_info(group, name, desc, 'Group')
class AccessibilityManager:
    '''
    Manages accessibility setup for the application.
    Usage:
        manager = AccessibilityManager()
        manager.setup_toolbar(toolbar)
        manager.setup_control_panel(control_panel)
    '''
    def __init__(self):
        self._focus_widgets = []
    def add_to_focus_order(self, widget = None):
        '''Add widget to the focus order list.'''
        self._focus_widgets.append(widget)
    def apply_focus_order(self):
        '''Apply the stored focus order.'''
        setup_focus_order(self._focus_widgets)
        self._focus_widgets.clear()
    def setup_toolbar_accessibility(self, toolbar):
        '''Set up accessibility for the toolbar.'''
        from ..ui.toolbar import Toolbar
        if not isinstance(toolbar, Toolbar):
            return None
        setup_button_accessibility(toolbar.open_btn, 'Open File', 'Open an image file for processing', 'Ctrl+O')
        setup_button_accessibility(toolbar.save_btn, 'Save File', 'Save the processed image', 'Ctrl+S')
        setup_button_accessibility(toolbar.brush_add_btn, 'Brush Add', 'Paint to add areas to the selection')
        setup_button_accessibility(toolbar.brush_remove_btn, 'Brush Remove', 'Paint to remove areas from the selection')
        setup_button_accessibility(toolbar.pan_btn, 'Pan Tool', 'Click and drag to pan around the image', 'Space (hold)')
        setup_button_accessibility(toolbar.undo_btn, 'Undo', 'Undo the last action', 'Ctrl+Z')
        setup_button_accessibility(toolbar.redo_btn, 'Redo', 'Redo the last undone action', 'Ctrl+Y')
        focus_widgets = [
            toolbar.open_btn,
            toolbar.save_btn,
            toolbar.brush_add_btn,
            toolbar.brush_remove_btn,
            toolbar.pan_btn,
            toolbar.undo_btn,
            toolbar.redo_btn]
        for w in focus_widgets:
            self.add_to_focus_order(w)
        logger.debug('Toolbar accessibility configured')
    def setup_control_panel_accessibility(self, panel):
        '''Set up accessibility for the control panel.'''
        from ..ui.control_panel import ControlPanel
        if not isinstance(panel, ControlPanel):
            return None
        setup_button_accessibility(panel.process_btn, 'Remove Background', 'Start processing the image to remove the background', 'Enter')
        self.add_to_focus_order(panel.process_btn)
        setup_combobox_accessibility(panel.bg_type_combo, 'Background Type', 'Choose the type of background: transparent, solid color, gradient, or image')
        self.add_to_focus_order(panel.bg_type_combo)
        setup_button_accessibility(panel.bg_color_btn, 'Background Color', 'Click to choose a solid background color')
        setup_combobox_accessibility(panel.gradient_combo, 'Gradient Preset', 'Choose a pre-defined gradient or customize')
        setup_button_accessibility(panel.gradient_color1_btn, 'Gradient Start Color', 'Click to choose the starting color of the gradient')
        setup_button_accessibility(panel.gradient_color2_btn, 'Gradient End Color', 'Click to choose the ending color of the gradient')
        setup_button_accessibility(panel.load_bg_image_btn, 'Load Background Image', 'Choose an image file to use as background')
        setup_combobox_accessibility(panel.fit_mode_combo, 'Image Fit Mode', 'How the background image fills the canvas: cover, contain, stretch, or tile')
        setup_slider_accessibility(panel.bg_blur_slider, 'Background Blur', 0, 30, 'px', 'Blur the background image')
        setup_checkbox_accessibility(panel.shadow_enabled_check, 'Enable Shadow', 'Add a drop shadow behind the subject')
        self.add_to_focus_order(panel.shadow_enabled_check)
        setup_combobox_accessibility(panel.shadow_preset_combo, 'Shadow Preset', 'Choose a pre-defined shadow style')
        self.add_to_focus_order(panel.shadow_preset_combo)
        setup_slider_accessibility(panel.shadow_blur_slider, 'Shadow Blur', 0, 100, 'px', 'How soft or hard the shadow edges are')
        self.add_to_focus_order(panel.shadow_blur_slider)
        setup_slider_accessibility(panel.shadow_opacity_slider, 'Shadow Opacity', 0, 100, '%', 'How dark or light the shadow is')
        self.add_to_focus_order(panel.shadow_opacity_slider)
        setup_slider_accessibility(panel.shadow_distance_slider, 'Shadow Distance', 0, 50, 'px', 'How far the shadow is from the subject')
        self.add_to_focus_order(panel.shadow_distance_slider)
        setup_button_accessibility(panel.shadow_color_btn, 'Shadow Color', 'Click to choose the shadow color')
        setup_slider_accessibility(panel.edge_sharp_slider, 'Edge Sharpness', -100, 100, '', 'Negative values soften edges, positive values sharpen')
        self.add_to_focus_order(panel.edge_sharp_slider)
        setup_slider_accessibility(panel.edge_expand_slider, 'Edge Expand', -10, 10, 'px', 'Negative values contract the selection, positive values expand')
        self.add_to_focus_order(panel.edge_expand_slider)
        setup_slider_accessibility(panel.edge_feather_slider, 'Edge Feather', 0, 20, 'px', 'Softens the edge transition')
        self.add_to_focus_order(panel.edge_feather_slider)
        setup_combobox_accessibility(panel.export_format_combo, 'Export Format', 'Choose the file format for export: PNG, JPEG, or WebP')
        self.add_to_focus_order(panel.export_format_combo)
        setup_slider_accessibility(panel.export_quality_slider, 'Export Quality', 1, 100, '%', 'Higher quality means larger file size')
        self.add_to_focus_order(panel.export_quality_slider)
        setup_button_accessibility(panel.export_btn, 'Export Image', 'Export the processed image to a file')
        self.add_to_focus_order(panel.export_btn)
        logger.debug('Control panel accessibility configured')
_accessibility_manager: Optional[AccessibilityManager] = None
def get_accessibility_manager():
    '''Get the global accessibility manager.'''
    global _accessibility_manager
    if _accessibility_manager is None:
        _accessibility_manager = AccessibilityManager()
    return _accessibility_manager
