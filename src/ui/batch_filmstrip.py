'''
Batch Filmstrip for QuestCut-AI
===========================
Horizontal filmstrip for navigating batch images with thumbnails.
'''
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QGridLayout, QLineEdit, QButtonGroup, QMenu
from PySide6.QtCore import Signal, Slot, Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QAction
from PIL import Image
from ..utils.i18n import tr
logger = logging.getLogger(__name__)
@dataclass
class BatchImageState:
    """State for a batch image. Fields set dynamically via kwargs."""
    def __init__(self, **kwargs):
        self.id = 0
        self.file_path = ''
        self.status = 'pending'
        self.original_image = None
        self.processed_image = None
        self.result_mask = None
        self.thumbnail = None
        self.error_message = ''
        self.has_custom_edits = False
        self.saved_path = ''
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def is_processing(self):
        return self.status == 'processing'

    @property
    def is_pending(self):
        return self.status in ('pending', 'processing')

    @property
    def is_processed(self):
        return self.status in ('processed', 'edited', 'saved')

    @property
    def has_error(self):
        return self.status == 'error' or bool(self.error_message)

    @property
    def filename(self):
        return Path(self.file_path).name if self.file_path else ''

    def clear_images(self, keep_results=True):
        self.original_image = None
        if not keep_results:
            self.processed_image = None
            self.result_mask = None

class FilmstripThumbnail(QFrame):
    '''Single thumbnail in the filmstrip.'''
    clicked = Signal(int)
    remove_clicked = Signal(int)
    def __init__(self, image_state = None, parent = None, defer_thumbnail = None):
        super().__init__(parent)
        self.image_state = image_state
        self._is_selected = False
        self._thumbnail_loaded = False
        self._setup_ui(defer_thumbnail)
    def _setup_ui(self, defer_thumbnail = None):
        self.setFixedSize(72, 64)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(68, 48)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet('background: #2a2a2f; border-radius: 4px;')
        layout.addWidget(self.thumb_label)
        self._close_btn = QPushButton('✕', self)
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.move(52, 2)
        self._close_btn.hide()
        self._close_btn.setCursor(Qt.ArrowCursor)
        self._close_btn.setStyleSheet('\n            QPushButton {\n                background-color: rgba(0, 0, 0, 0.7);\n                border: none;\n                border-radius: 9px;\n                color: #ffffff;\n                font-size: 10px;\n                font-weight: bold;\n                padding: 0px;\n            }\n            QPushButton:hover {\n                background-color: #ef4444;\n            }\n        ')
        self._close_btn.clicked.connect(lambda: self.remove_clicked.emit(self.image_state.id))
        self.status_label = QLabel()
        self.status_label.setFixedHeight(12)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('font-size: 9px;')
        layout.addWidget(self.status_label)
        self._update_style()
        if not defer_thumbnail:
            self._load_thumbnail()
            return None
    def _load_thumbnail(self):
        '''Load thumbnail from image state or file.'''
        if self.image_state.thumbnail:
            self.thumb_label.setPixmap(self.image_state.thumbnail)
            self._thumbnail_loaded = True
            return None
        img = self.image_state.processed_image
        if img is None:
            img = self.image_state.original_image
        if img is None:
            path_to_load = getattr(self.image_state, 'saved_path', '') or self.image_state.file_path
            with Image.open(path_to_load) as f:
                f.load()
                img = f.copy()
        img_copy = img.copy()
        img_copy.thumbnail((68, 48), Image.Resampling.LANCZOS)
        if img_copy.mode == 'RGBA':
            bg = Image.new('RGB', img_copy.size, (42, 42, 47))
            bg.paste(img_copy, img_copy.split()[3])
            img_copy = bg
        elif img_copy.mode != 'RGB':
            img_copy = img_copy.convert('RGB')
        data = img_copy.tobytes('raw', 'RGB')
        qimg = QImage(data, img_copy.width, img_copy.height, img_copy.width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.image_state.thumbnail = pixmap
        self.thumb_label.setPixmap(pixmap)
        self._thumbnail_loaded = True
    def _update_style(self):
        '''Update visual style based on state.'''
        status = self.image_state.status
        if self._is_selected:
            border_color = '#4F46E5'
            border_width = '2px'
            bg = 'rgba(79, 70, 229, 0.15)'
        else:
            border_width = '1px'
            bg = '#1a1a1d'
            if status == 'error':
                border_color = '#ef4444'
            elif status == 'processing':
                border_color = '#f59e0b'
            elif status == 'edited':
                border_color = '#22c55e'
            elif status == 'processed':
                border_color = '#3a3a40'
            else:
                border_color = '#2a2a2f'
        self.setStyleSheet(f'''\n            FilmstripThumbnail {{\n                background-color: {bg};\n                border: {border_width} solid {border_color};\n                border-radius: 6px;\n            }}\n        ''')
        status_icons = {
            'pending': '',
            'processing': '...',
            'processed': '✓',
            'edited': '✓✎',
            'error': '✗' }
        status_colors = {
            'pending': '#606065',
            'processing': '#f59e0b',
            'processed': '#22c55e',
            'edited': '#4F46E5',
            'error': '#ef4444' }
        self.status_label.setText(status_icons.get(status, ''))
        self.status_label.setStyleSheet(f'''font-size: 9px; color: {status_colors.get(status, '#606065')};''')
    def set_selected(self, selected = None):
        '''Set selection state.'''
        self._is_selected = selected
        self._update_style()
    def refresh(self):
        '''Refresh the thumbnail display.'''
        self._load_thumbnail()
        self._update_style()
    def enterEvent(self, event = None):
        '''Show close button on hover.'''
        self._close_btn.show()
        super().enterEvent(event)
    def leaveEvent(self, event = None):
        '''Hide close button when not hovering.'''
        self._close_btn.hide()
        super().leaveEvent(event)
    def contextMenuEvent(self, event):
        '''Right-click context menu.'''
        menu = QMenu(self)
        menu.setStyleSheet('\n            QMenu {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 6px;\n                padding: 4px;\n                color: #ffffff;\n            }\n            QMenu::item {\n                padding: 6px 20px;\n                border-radius: 4px;\n            }\n            QMenu::item:selected {\n                background-color: #3a3a40;\n            }\n        ')
        remove_action = menu.addAction(tr('Remove Image'))
        action = menu.exec(event.globalPos())
        if action == remove_action:
            self.remove_clicked.emit(self.image_state.id)
            return None
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_state.id)
            return None
class BatchFilmstrip(QWidget):
    '''
    Batch image navigation with filmstrip and grid view modes.
    Features:
    - Filmstrip mode: scrollable horizontal thumbnails
    - Grid mode: multi-row grid with larger thumbnails
    - Filter by status: All, Pending, Done, Failed, Edited
    - Jump-to-image by number
    - Keyboard navigation (arrow keys, Home, End)
    - Status badges per image
    '''
    image_selected = Signal(int)
    image_removed = Signal(int)
    add_images_clicked = Signal()
    thumbnails_loading = Signal(int, int)
    thumbnails_loaded = Signal()
    _THUMB_BATCH_SIZE = 20
    def __init__(self, parent = None):
        super().__init__(parent)
        self._images = []
        self._filtered_images = []
        self._thumbnails = { }
        self._grid_thumbnails = { }
        self._current_index = 0
        self._view_mode = 'filmstrip'
        self._filter = 'all'
        self._filter_labels = {
            'all': 'All',
            'pending': 'Pending',
            'processed': 'Done',
            'failed': 'Failed',
            'edited': 'Edited',
        }
        self._pending_thumb_loads = []
        self._total_deferred = 0
        self._setup_ui()
        self.setFocusPolicy(Qt.StrongFocus)
    def _setup_ui(self):
        self.setFixedHeight(130)
        self.setStyleSheet('\n            BatchFilmstrip {\n                background-color: #0f0f10;\n                border-top: 1px solid #2a2a2f;\n            }\n        ')
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)
        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet('background: transparent;')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        self.strip_view_btn = QPushButton(tr('Strip'))
        self.strip_view_btn.setCheckable(True)
        self.strip_view_btn.setChecked(True)
        self.strip_view_btn.setFixedHeight(22)
        self.strip_view_btn.setStyleSheet(self._toggle_btn_style())
        self.strip_view_btn.clicked.connect(lambda: self._set_view_mode('filmstrip'))
        self._view_group.addButton(self.strip_view_btn)
        header_layout.addWidget(self.strip_view_btn)
        self.grid_view_btn = QPushButton(tr('Grid'))
        self.grid_view_btn.setCheckable(True)
        self.grid_view_btn.setFixedHeight(22)
        self.grid_view_btn.setStyleSheet(self._toggle_btn_style())
        self.grid_view_btn.clicked.connect(lambda: self._set_view_mode('grid'))
        self._view_group.addButton(self.grid_view_btn)
        header_layout.addWidget(self.grid_view_btn)
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedHeight(16)
        sep.setStyleSheet('color: #3a3a40;')
        header_layout.addWidget(sep)
        self._filter_buttons = { }
        for filter_key, label in self._filter_labels.items():
            btn = QPushButton(tr(label))
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setStyleSheet(self._filter_btn_style())
            btn.clicked.connect(lambda checked=None, k=filter_key: self._set_filter(k))
            header_layout.addWidget(btn)
            self._filter_buttons[filter_key] = btn
        self._filter_buttons['all'].setChecked(True)
        self.add_images_btn = QPushButton('+ ' + tr('Add Images'))
        self.add_images_btn.setFixedHeight(22)
        self.add_images_btn.setCursor(Qt.PointingHandCursor)
        self.add_images_btn.setStyleSheet('\n            QPushButton {\n                background-color: transparent;\n                border: 1px solid #4F46E5;\n                border-radius: 4px;\n                padding: 0 10px;\n                color: #4F46E5;\n                font-size: 10px;\n                font-weight: bold;\n            }\n            QPushButton:hover {\n                background-color: rgba(79, 70, 229, 0.15);\n                color: #ffffff;\n            }\n        ')
        self.add_images_btn.clicked.connect(self.add_images_clicked.emit)
        header_layout.addWidget(self.add_images_btn)
        header_layout.addStretch()
        self.jump_label = QLabel(tr('Go to:'))
        self.jump_label.setStyleSheet('color: #606065; font-size: 10px; background: transparent;')
        header_layout.addWidget(self.jump_label)
        self.jump_input = QLineEdit()
        self.jump_input.setPlaceholderText('#')
        self.jump_input.setFixedSize(40, 22)
        self.jump_input.setStyleSheet('\n            QLineEdit {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                padding: 0 4px;\n                color: #ffffff;\n                font-size: 11px;\n            }\n            QLineEdit:focus {\n                border-color: #4F46E5;\n            }\n        ')
        self.jump_input.returnPressed.connect(self._on_jump_to)
        header_layout.addWidget(self.jump_input)
        self.counter_label = QLabel('0/0')
        self.counter_label.setFixedWidth(50)
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet('color: #a0a0a5; font-size: 11px; background: transparent;')
        header_layout.addWidget(self.counter_label)
        main_layout.addWidget(header)
        self.filmstrip_widget = QWidget()
        self.filmstrip_widget.setStyleSheet('background: transparent;')
        filmstrip_layout = QHBoxLayout(self.filmstrip_widget)
        filmstrip_layout.setContentsMargins(0, 0, 0, 0)
        filmstrip_layout.setSpacing(8)
        self.left_btn = QPushButton('◀')
        self.left_btn.setFixedSize(28, 64)
        self.left_btn.setStyleSheet(self._arrow_btn_style())
        self.left_btn.clicked.connect(self._go_previous)
        filmstrip_layout.addWidget(self.left_btn)
        self.filmstrip_scroll = QScrollArea()
        self.filmstrip_scroll.setWidgetResizable(True)
        self.filmstrip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filmstrip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filmstrip_scroll.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        self.thumb_container = QWidget()
        self.thumb_container.setStyleSheet('background: transparent;')
        self.thumb_layout = QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_layout.setSpacing(6)
        self.thumb_layout.setAlignment(Qt.AlignLeft)
        self.filmstrip_scroll.setWidget(self.thumb_container)
        filmstrip_layout.addWidget(self.filmstrip_scroll, 1)
        self.right_btn = QPushButton('▶')
        self.right_btn.setFixedSize(28, 64)
        self.right_btn.setStyleSheet(self._arrow_btn_style())
        self.right_btn.clicked.connect(self._go_next)
        filmstrip_layout.addWidget(self.right_btn)
        main_layout.addWidget(self.filmstrip_widget)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.grid_scroll.setStyleSheet('\n            QScrollArea { background: transparent; border: none; }\n            QScrollBar:vertical {\n                width: 6px;\n                background: transparent;\n            }\n            QScrollBar::handle:vertical {\n                background: #3a3a40;\n                border-radius: 3px;\n            }\n        ')
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet('background: transparent;')
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(6)
        self.grid_scroll.setWidget(self.grid_container)
        self.grid_scroll.hide()
        main_layout.addWidget(self.grid_scroll)
        self._update_navigation()
    def _toggle_btn_style(self):
        return '\n            QPushButton {\n                background-color: transparent;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                padding: 0 8px;\n                color: #a0a0a5;\n                font-size: 10px;\n            }\n            QPushButton:hover {\n                border-color: #4F46E5;\n                color: #ffffff;\n            }\n            QPushButton:checked {\n                background-color: #4F46E5;\n                border-color: #4F46E5;\n                color: #ffffff;\n            }\n        '
    def _filter_btn_style(self):
        return '\n            QPushButton {\n                background-color: transparent;\n                border: 1px solid transparent;\n                border-radius: 4px;\n                padding: 0 6px;\n                color: #606065;\n                font-size: 10px;\n            }\n            QPushButton:hover {\n                color: #a0a0a5;\n                border-color: #3a3a40;\n            }\n            QPushButton:checked {\n                color: #ffffff;\n                border-color: #4F46E5;\n                background-color: rgba(79, 70, 229, 0.15);\n            }\n        '
    def _arrow_btn_style(self):
        return '\n            QPushButton {\n                background-color: #2a2a2f;\n                border: 1px solid #3a3a40;\n                border-radius: 4px;\n                color: #a0a0a5;\n                font-size: 14px;\n            }\n            QPushButton:hover {\n                background-color: #3a3a40;\n                color: #ffffff;\n            }\n            QPushButton:disabled {\n                color: #3a3a40;\n            }\n        '
    def _set_view_mode(self, mode = None):
        '''Switch between filmstrip and grid view.'''
        self._view_mode = mode
        if mode == 'filmstrip':
            self.setFixedHeight(130)
            self.grid_scroll.hide()
            self.filmstrip_widget.show()
        else:
            self.setMinimumHeight(130)
            self.setMaximumHeight(350)
            self.filmstrip_widget.hide()
            self.grid_scroll.show()
        self._rebuild_thumbnails()
    def _set_filter(self, filter_key = None):
        '''Set the active filter.'''
        self._filter = filter_key
        for key, btn in self._filter_buttons.items():
            btn.setChecked(key == filter_key)
        self._apply_filter()
        self._rebuild_thumbnails()
    def _apply_filter(self):
        '''Apply current filter to images.'''
        if self._filter == 'all':
            self._filtered_images = list(self._images)
        elif self._filter == 'pending':
            self._filtered_images = [img for img in self._images if img.is_pending]
        elif self._filter == 'processed':
            self._filtered_images = [img for img in self._images if img.is_processed]
        elif self._filter == 'failed':
            self._filtered_images = [img for img in self._images if img.has_error]
        elif self._filter == 'edited':
            self._filtered_images = [img for img in self._images if img.has_custom_edits]
        self._update_filter_counts()
    def _update_filter_counts(self):
        """Update filter button labels with counts."""
        counts = {
            'all': len(self._images),
            'pending': sum(1 for img in self._images if img.is_pending),
            'processed': sum(1 for img in self._images if img.is_processed),
            'failed': sum(1 for img in self._images if img.has_error),
            'edited': sum(1 for img in self._images if img.has_custom_edits),
        }
        for key, btn in self._filter_buttons.items():
            btn.setText(f"{tr(self._filter_labels[key])} ({counts.get(key, 0)})")

    def retranslate_ui(self):
        """Refresh language-dependent labels."""
        self.strip_view_btn.setText(tr('Strip'))
        self.grid_view_btn.setText(tr('Grid'))
        self.add_images_btn.setText('+ ' + tr('Add Images'))
        self.jump_label.setText(tr('Go to:'))
        self._update_filter_counts()

    def set_images(self, images=None):
        """Set the images list and rebuild thumbnails."""
        self._images = images or []
        self._current_index = 0
        self._apply_filter()
        self._rebuild_thumbnails()

    def _update_navigation(self):
        """Update counter label and arrow button states."""
        total = len(self._filtered_images)
        if total > 0:
            self.counter_label.setText(f'{self._current_index + 1}/{total}')
        else:
            self.counter_label.setText('0/0')
        self.left_btn.setEnabled(self._current_index > 0)
        self.right_btn.setEnabled(self._current_index < total - 1)

    def _select_current(self):
        """Highlight the current thumbnail in both views."""
        for idx, thumb in self._thumbnails.items():
            thumb.set_selected(idx == self._current_index)
        for idx, thumb in self._grid_thumbnails.items():
            thumb.set_selected(idx == self._current_index)

    def _go_previous(self):
        """Navigate to the previous image."""
        if self._current_index > 0:
            self._current_index -= 1
            self._select_current()
            self._update_navigation()
            if self._filtered_images:
                self.image_selected.emit(self._filtered_images[self._current_index].id)

    def _go_next(self):
        """Navigate to the next image."""
        if self._current_index < len(self._filtered_images) - 1:
            self._current_index += 1
            self._select_current()
            self._update_navigation()
            if self._filtered_images:
                self.image_selected.emit(self._filtered_images[self._current_index].id)

    def _on_jump_to(self):
        """Jump to an image by its number."""
        try:
            num = int(self.jump_input.text()) - 1
            if 0 <= num < len(self._filtered_images):
                self._current_index = num
                self._select_current()
                self._update_navigation()
                self.image_selected.emit(self._filtered_images[num].id)
        except ValueError:
            pass
        self.jump_input.clear()

    def _rebuild_thumbnails(self):
        """Clear and rebuild all thumbnail widgets for current view mode."""
        # Clear existing thumbnails
        for thumb in self._thumbnails.values():
            thumb.setParent(None)
        self._thumbnails.clear()
        for thumb in self._grid_thumbnails.values():
            thumb.setParent(None)
        self._grid_thumbnails.clear()

        # Clear layouts
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if not self._filtered_images:
            self._update_navigation()
            return

        self._total_deferred = 0
        self._pending_thumb_loads = []

        for idx, img_state in enumerate(self._filtered_images):
            defer = idx >= self._THUMB_BATCH_SIZE
            film_thumb = FilmstripThumbnail(img_state, self, defer_thumbnail=defer)
            film_thumb.clicked.connect(self._on_thumbnail_clicked)
            film_thumb.remove_clicked.connect(self.image_removed.emit)
            self._thumbnails[idx] = film_thumb
            self.thumb_layout.addWidget(film_thumb)

            grid_thumb = FilmstripThumbnail(img_state, self, defer_thumbnail=defer)
            grid_thumb.clicked.connect(self._on_thumbnail_clicked)
            grid_thumb.remove_clicked.connect(self.image_removed.emit)
            row, col = divmod(idx, 4)
            self._grid_thumbnails[idx] = grid_thumb
            self.grid_layout.addWidget(grid_thumb, row, col)

            if defer:
                self._pending_thumb_loads.append(img_state)
                self._total_deferred += 1

        if self._total_deferred > 0:
            self.thumbnails_loading.emit(0, self._total_deferred)
            QTimer.singleShot(50, self._load_remaining_thumbnails)
        else:
            self.thumbnails_loaded.emit()

        self.thumb_layout.addStretch()
        self._update_navigation()
        self._select_current()

    def _on_thumbnail_clicked(self, img_id):
        """Handle a thumbnail being clicked."""
        for idx, img in enumerate(self._filtered_images):
            if img.id == img_id:
                self._current_index = idx
                self._select_current()
                self._update_navigation()
                self.image_selected.emit(img_id)
                break

    def _load_remaining_thumbnails(self):
        """Deferred loading of remaining thumbnails in batches."""
        batch = self._pending_thumb_loads[:self._THUMB_BATCH_SIZE]
        del self._pending_thumb_loads[:self._THUMB_BATCH_SIZE]
        for img_state in batch:
            thumb_id = None
            for idx, img in enumerate(self._filtered_images):
                if img.id == img_state.id:
                    thumb_id = idx
                    break
            if thumb_id is not None and thumb_id in self._thumbnails:
                self._thumbnails[thumb_id]._load_thumbnail()
                if thumb_id in self._grid_thumbnails:
                    self._grid_thumbnails[thumb_id]._load_thumbnail()
        loaded = self._total_deferred - len(self._pending_thumb_loads)
        self.thumbnails_loading.emit(loaded, self._total_deferred)
        if self._pending_thumb_loads:
            QTimer.singleShot(50, self._load_remaining_thumbnails)
        else:
            self.thumbnails_loaded.emit()

    def refresh_all(self):
        """Refresh all thumbnail widgets."""
        for thumb in self._thumbnails.values():
            thumb.refresh()
        for thumb in self._grid_thumbnails.values():
            thumb.refresh()

    def release_processed_images(self):
        """Release source image references while keeping processed results visible."""
        for img in self._images:
            if hasattr(img, 'clear_images'):
                try:
                    img.clear_images()
                except Exception:
                    pass

    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        if event.key() == Qt.Key_Left:
            self._go_previous()
        elif event.key() == Qt.Key_Right:
            self._go_next()
        elif event.key() == Qt.Key_Home:
            if self._filtered_images:
                self._current_index = 0
                self._select_current()
                self._update_navigation()
                self.image_selected.emit(self._filtered_images[0].id)
        elif event.key() == Qt.Key_End:
            if self._filtered_images:
                self._current_index = len(self._filtered_images) - 1
                self._select_current()
                self._update_navigation()
                self.image_selected.emit(self._filtered_images[-1].id)
        else:
            super().keyPressEvent(event)
