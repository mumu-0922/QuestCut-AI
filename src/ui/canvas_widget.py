"""
Canvas Widget for QuestCut-AI
=========================
Image display with comparison slider, zoom/pan, and brush tools.
"""
import logging
import math
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QPointF, QRect, QRectF, QSize, QLineF, QTimer, Property, QEvent
from PySide6.QtGui import QPainter, QPixmap, QImage, QPen, QColor, QBrush, QPainterPath, QCursor, QFont, QConicalGradient, QLinearGradient
from PIL import Image
from ..utils.image_utils import pil_to_qpixmap
from ..processing.background import BackgroundGenerator
from ..utils.i18n import tr
from .canvas_helpers import fit_zoom, image_rect

logger = logging.getLogger(__name__)


class ViewMode(Enum):
    RESULT = 'result'
    ORIGINAL = 'original'
    COMPARISON = 'comparison'
    SIDE_BY_SIDE = 'side_by_side'


class CanvasWidget(QWidget):
    brush_stroke = Signal(list, int, bool)
    zoom_changed = Signal(float)
    view_mode_changed = Signal(str)
    file_dropped = Signal(str)
    files_dropped = Signal(list)

    SLIDER_WIDTH = 4
    SLIDER_HANDLE_SIZE = 24
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10
    CHECKERBOARD_SIZE = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self._result_pixmap = None
        self._checkerboard = None
        self._view_mode = ViewMode.RESULT
        self._zoom = 1
        self._pan_offset = QPointF(0, 0)
        self._slider_position = 0.5
        self._is_dragging_slider = False
        self._slider_hover = False
        self._current_tool = 'none'
        self._brush_radius = 20
        self._brush_is_add = True
        self._is_panning = False
        self._is_painting = False
        self._last_mouse_pos = QPointF()
        self._brush_points = []
        self._touch_points = {}
        self._initial_pinch_distance = 0
        self._initial_zoom = 1
        self._is_drag_over = False
        self._animation_angle = 0
        self._pulse_value = 0
        self._reveal_progress = 0
        self._is_revealing = False
        self._bg_gen = BackgroundGenerator()
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self._update_checkerboard()
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_timer.start(30)
        self._checkerboard_timer = QTimer(self)
        self._checkerboard_timer.setSingleShot(True)
        self._checkerboard_timer.setInterval(150)
        self._checkerboard_timer.timeout.connect(self._update_checkerboard)

    def _update_animation(self):
        self._animation_angle = (self._animation_angle + 2) % 360
        self._pulse_value = (math.sin(self._animation_angle * 0.05) + 1) / 2
        if self._is_revealing:
            self._reveal_progress = min(1, self._reveal_progress + 0.03)
            if self._reveal_progress >= 1:
                self._is_revealing = False
        if self._original_pixmap is None and (self._is_drag_over or self._is_revealing):
            self.update()
        elif hasattr(self, '_animation_timer') and self._animation_timer.isActive():
            if self._original_pixmap is not None and not self._is_drag_over and not self._is_revealing:
                self._animation_timer.stop()

    def set_image(self, image=None):
        """Set the source image displayed on the canvas."""
        if image is None:
            self.clear()
            return
        if isinstance(image, QPixmap):
            self._original_pixmap = QPixmap(image)
        elif isinstance(image, QImage):
            self._original_pixmap = QPixmap.fromImage(image)
        else:
            self._original_pixmap = pil_to_qpixmap(image)
        self._result_pixmap = None
        self._view_mode = ViewMode.RESULT
        self._pan_offset = QPointF(0, 0)
        self._slider_position = 0.5
        self._is_revealing = False
        self._reveal_progress = 0
        self._fit_to_view()
        if hasattr(self, '_animation_timer') and not self._animation_timer.isActive():
            self._animation_timer.start(30)
        self.update()

    def set_result_image(self, image=None):
        """Set the processed/result image displayed on the canvas."""
        if image is None:
            self._result_pixmap = None
            self.update()
            return
        if isinstance(image, QPixmap):
            self._result_pixmap = QPixmap(image)
        elif isinstance(image, QImage):
            self._result_pixmap = QPixmap.fromImage(image)
        else:
            self._result_pixmap = pil_to_qpixmap(image)
        self._view_mode = ViewMode.RESULT
        if self._original_pixmap is None:
            self._fit_to_view()
        self.update()

    def set_result(self, image=None, animate=None):
        """Set a result image and optionally reveal it with animation."""
        self.set_result_image(image)
        if animate is None:
            animate = True
        self._is_revealing = bool(animate and self._original_pixmap and self._result_pixmap)
        self._reveal_progress = 0 if self._is_revealing else 1
        if self._is_revealing and hasattr(self, '_animation_timer') and not self._animation_timer.isActive():
            self._animation_timer.start(30)
        self.update()

    def update_result_silent(self, image=None):
        """Update result without changing zoom/pan or playing reveal animation."""
        if image is None:
            self._result_pixmap = None
        elif isinstance(image, QPixmap):
            self._result_pixmap = QPixmap(image)
        elif isinstance(image, QImage):
            self._result_pixmap = QPixmap.fromImage(image)
        else:
            self._result_pixmap = pil_to_qpixmap(image)
        self._is_revealing = False
        self._reveal_progress = 1
        self.update()

    def clear(self):
        self._original_pixmap = None
        self._result_pixmap = None
        self._view_mode = ViewMode.RESULT
        self._current_tool = 'none'
        self._is_painting = False
        self._brush_points = []
        if hasattr(self, '_animation_timer') and not self._animation_timer.isActive():
            self._animation_timer.start(30)
        self.update()

    def show_original(self):
        self._view_mode = ViewMode.ORIGINAL
        self.view_mode_changed.emit('original')
        self.update()

    def show_result(self):
        self._view_mode = ViewMode.RESULT
        self.view_mode_changed.emit('result')
        self.update()

    def set_view_mode(self, mode=None):
        mode_map = {
            'result': ViewMode.RESULT,
            'original': ViewMode.ORIGINAL,
            'comparison': ViewMode.COMPARISON,
            'side_by_side': ViewMode.SIDE_BY_SIDE,
        }
        if mode in mode_map:
            self._view_mode = mode_map[mode]
            self.view_mode_changed.emit(mode)
            self.update()

    def toggle_view(self):
        if self._original_pixmap or self._result_pixmap:
            if self._view_mode == ViewMode.RESULT:
                self._view_mode = ViewMode.ORIGINAL
            elif self._view_mode == ViewMode.ORIGINAL:
                self._view_mode = ViewMode.RESULT
            else:
                self._view_mode = ViewMode.RESULT
            self.update()

    def enable_comparison_slider(self):
        if self._original_pixmap or self._result_pixmap:
            self._view_mode = ViewMode.COMPARISON
            self._slider_position = 0.5
            self.update()

    def set_tool(self, tool=None):
        if self._is_painting and self._brush_points:
            self.brush_stroke.emit(self._brush_points, self._brush_radius, self._brush_is_add)
        self._is_panning = False
        self._is_painting = False
        self._brush_points = []
        self._current_tool = tool
        self._update_cursor()

    def set_brush_size(self, size=None):
        self._brush_radius = max(1, min(100, size))
        self.update()

    def set_brush_mode(self, is_add=None):
        self._brush_is_add = is_add

    def zoom_in(self):
        self._set_zoom(self._zoom * 1.2)

    def zoom_out(self):
        self._set_zoom(self._zoom / 1.2)

    def zoom_fit(self):
        self._fit_to_view()

    def zoom_100(self):
        self._set_zoom(1)

    def get_slider_position(self):
        return self._slider_position

    def set_slider_position(self, position=None):
        self._slider_position = max(0, min(1, position))
        self.update()

    def _set_zoom(self, zoom=None, center=None):
        old_zoom = self._zoom
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        if center and old_zoom != self._zoom:
            scale_factor = self._zoom / old_zoom
            self._pan_offset = center - (center - self._pan_offset) * scale_factor
        self.zoom_changed.emit(self._zoom)
        self.update()

    def _fit_to_view(self):
        pixmap = self._get_display_pixmap()
        if pixmap is None:
            return
        img_size = pixmap.size()
        view_size = self.size()
        if img_size.width() <= 0 or img_size.height() <= 0:
            self._zoom = 1
            return
        if self._view_mode == ViewMode.SIDE_BY_SIDE:
            view_size = QSize(view_size.width() // 2 - 20, view_size.height())
        if view_size.width() <= 0 or view_size.height() <= 0:
            self._zoom = 1
            return
        self._zoom = fit_zoom(img_size, view_size)
        self._pan_offset = QPointF(0, 0)
        self.zoom_changed.emit(self._zoom)
        self.update()

    def _get_display_pixmap(self):
        if self._view_mode == ViewMode.ORIGINAL:
            return self._original_pixmap
        if self._result_pixmap is not None:
            return self._result_pixmap
        return self._original_pixmap

    def _update_checkerboard(self):
        size = max(self.width(), self.height()) + 100
        checkerboard = self._bg_gen.create_checkerboard((size, size), self.CHECKERBOARD_SIZE)
        self._checkerboard = pil_to_qpixmap(checkerboard)

    def _update_cursor(self):
        if self._slider_hover:
            self.setCursor(Qt.SplitHCursor)
        elif self._current_tool == 'brush':
            self.setCursor(Qt.CrossCursor)
        elif self._current_tool == 'pan' or self._is_panning:
            if self._is_panning:
                self.setCursor(Qt.ClosedHandCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _get_image_rect(self):
        pixmap = self._get_display_pixmap()
        if pixmap is None:
            return QRectF()
        return image_rect(self.size(), pixmap.size(), self._zoom, self._pan_offset)

    def _widget_to_image(self, pos=None):
        rect = self._get_image_rect()
        if not rect.isValid():
            return (0, 0)
        img_x = int((pos.x() - rect.x()) / self._zoom)
        img_y = int((pos.y() - rect.y()) / self._zoom)
        return (img_x, img_y)

    def _get_slider_rect(self):
        rect = self._get_image_rect()
        if not rect.isValid():
            return QRectF()
        x = rect.x() + rect.width() * self._slider_position
        y = rect.y()
        height = rect.height()
        return QRectF(x - self.SLIDER_HANDLE_SIZE / 2, y + height / 2 - self.SLIDER_HANDLE_SIZE / 2, self.SLIDER_HANDLE_SIZE, self.SLIDER_HANDLE_SIZE)

    def _is_over_slider(self, pos=None):
        if self._view_mode != ViewMode.COMPARISON:
            return False
        rect = self._get_image_rect()
        if not rect.isValid():
            return False
        slider_x = rect.x() + rect.width() * self._slider_position
        return abs(pos.x() - slider_x) < self.SLIDER_HANDLE_SIZE

    def paintEvent(self, event=None):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor('#0f0f10'))

        if self._view_mode == ViewMode.SIDE_BY_SIDE:
            self._paint_side_by_side(painter)
        elif self._view_mode == ViewMode.COMPARISON:
            self._paint_comparison(painter)
        else:
            self._paint_single(painter)

        if self._is_painting and self._brush_points and self._current_tool == 'brush':
            self._draw_active_stroke(painter)
        if self._current_tool == 'brush' and self.underMouse():
            self._draw_brush_cursor(painter)
        painter.end()

    def _paint_single(self, painter=None):
        if self._view_mode == ViewMode.ORIGINAL:
            pixmap = self._original_pixmap
        elif self._result_pixmap is not None:
            pixmap = self._result_pixmap
        else:
            pixmap = self._original_pixmap

        if pixmap is None:
            self._paint_empty(painter)
            return

        rect = self._get_image_rect()
        if self._checkerboard:
            painter.drawPixmap(rect.toRect(), self._checkerboard, QRect(0, 0, int(rect.width()), int(rect.height())))

        if self._is_revealing and self._result_pixmap and self._original_pixmap:
            painter.drawPixmap(rect.toRect(), self._original_pixmap)
            reveal_width = rect.width() * self._reveal_progress
            reveal_rect = QRectF(rect.x(), rect.y(), reveal_width, rect.height())
            painter.save()
            painter.setClipRect(reveal_rect)
            painter.drawPixmap(rect.toRect(), self._result_pixmap)
            painter.restore()
            if self._reveal_progress < 1:
                line_x = rect.x() + reveal_width
                pen = QPen(QColor('#4F46E5'), 3)
                painter.setPen(pen)
                painter.drawLine(QPointF(line_x, rect.y()), QPointF(line_x, rect.bottom()))
                glow = QLinearGradient(line_x - 20, 0, line_x + 5, 0)
                glow.setColorAt(0, QColor(79, 70, 229, 0))
                glow.setColorAt(0.8, QColor(79, 70, 229, 100))
                glow.setColorAt(1, QColor(79, 70, 229, 0))
                painter.fillRect(QRectF(line_x - 20, rect.y(), 25, rect.height()), glow)
        else:
            painter.drawPixmap(rect.toRect(), pixmap)

    def _paint_comparison(self, painter=None):
        if not self._original_pixmap or not self._result_pixmap:
            self._paint_single(painter)
            return

        rect = self._get_image_rect()
        slider_x = rect.x() + rect.width() * self._slider_position

        if self._checkerboard:
            painter.drawPixmap(rect.toRect(), self._checkerboard, QRect(0, 0, int(rect.width()), int(rect.height())))

        painter.save()
        left_clip = QRectF(rect.x(), rect.y(), slider_x - rect.x(), rect.height())
        painter.setClipRect(left_clip)
        painter.drawPixmap(rect.toRect(), self._original_pixmap)
        painter.restore()

        painter.save()
        right_clip = QRectF(slider_x, rect.y(), rect.right() - slider_x, rect.height())
        painter.setClipRect(right_clip)
        painter.drawPixmap(rect.toRect(), self._result_pixmap)
        painter.restore()

        pen = QPen(QColor('#ffffff'), self.SLIDER_WIDTH)
        painter.setPen(pen)
        painter.drawLine(QLineF(slider_x, rect.y(), slider_x, rect.bottom()))

        handle_rect = self._get_slider_rect()
        if handle_rect.isValid():
            painter.setBrush(QBrush(QColor('#4F46E5')))
            painter.setPen(QPen(QColor('#ffffff'), 2))
            painter.drawEllipse(handle_rect)
            painter.setPen(QPen(QColor('#ffffff'), 2))
            center = handle_rect.center()
            arrow_size = 4
            painter.drawLine(QPointF(center.x() - 3, center.y()), QPointF(center.x() - 3 - arrow_size, center.y() - arrow_size))
            painter.drawLine(QPointF(center.x() - 3, center.y()), QPointF(center.x() - 3 - arrow_size, center.y() + arrow_size))
            painter.drawLine(QPointF(center.x() + 3, center.y()), QPointF(center.x() + 3 + arrow_size, center.y() - arrow_size))
            painter.drawLine(QPointF(center.x() + 3, center.y()), QPointF(center.x() + 3 + arrow_size, center.y() + arrow_size))

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(QRectF(rect.x() + 10, rect.y() + 10, 100, 20), Qt.AlignLeft, tr('Original'))
        painter.drawText(QRectF(rect.right() - 110, rect.y() + 10, 100, 20), Qt.AlignRight, tr('Result'))

    def _paint_side_by_side(self, painter=None):
        if not self._original_pixmap:
            self._paint_empty(painter)
            return

        half_width = self.width() // 2
        gap = 10
        left_rect = QRectF(gap, gap, half_width - gap * 2, self.height() - gap * 2)
        if self._original_pixmap:
            self._draw_fitted_pixmap(painter, self._original_pixmap, left_rect)

        right_rect = QRectF(half_width + gap, gap, half_width - gap * 2, self.height() - gap * 2)
        pixmap = self._result_pixmap if self._result_pixmap else self._original_pixmap
        if pixmap:
            self._draw_fitted_pixmap(painter, pixmap, right_rect)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(QRectF(gap + 10, gap + 10, 100, 20), Qt.AlignLeft, tr('Original'))
        painter.drawText(QRectF(half_width + gap + 10, gap + 10, 100, 20), Qt.AlignLeft, tr('Result'))
        painter.setPen(QPen(QColor('#2a2a2f'), 2))
        painter.drawLine(half_width, 0, half_width, self.height())

    def _draw_fitted_pixmap(self, painter=None, pixmap=None, rect=None):
        scale = min(rect.width() / pixmap.width(), rect.height() / pixmap.height())
        scaled_w = pixmap.width() * scale
        scaled_h = pixmap.height() * scale
        x = rect.x() + (rect.width() - scaled_w) / 2
        y = rect.y() + (rect.height() - scaled_h) / 2
        target_rect = QRectF(x, y, scaled_w, scaled_h)
        if self._checkerboard:
            painter.drawPixmap(target_rect.toRect(), self._checkerboard, QRect(0, 0, int(scaled_w), int(scaled_h)))
        painter.drawPixmap(target_rect.toRect(), pixmap)

    def _paint_empty(self, painter=None):
        center_x = self.width() / 2
        center_y = self.height() / 2
        zone_width = min(500, self.width() - 80)
        zone_height = min(400, self.height() - 80)
        zone_rect = QRectF(center_x - zone_width / 2, center_y - zone_height / 2, zone_width, zone_height)
        self._draw_animated_border(painter, zone_rect)
        if self._is_drag_over:
            self._draw_drag_over_state(painter, zone_rect)
        else:
            self._draw_welcome_state(painter, zone_rect)

    def _draw_animated_border(self, painter=None, rect=None):
        painter.save()
        gradient = QConicalGradient(rect.center(), self._animation_angle)
        if self._is_drag_over:
            gradient.setColorAt(0, QColor('#4F46E5'))
            gradient.setColorAt(0.25, QColor('#818CF8'))
            gradient.setColorAt(0.5, QColor('#4F46E5'))
            gradient.setColorAt(0.75, QColor('#818CF8'))
            gradient.setColorAt(1, QColor('#4F46E5'))
            border_width = 4
        else:
            gradient.setColorAt(0, QColor('#3a3a40'))
            gradient.setColorAt(0.25, QColor('#4F46E5'))
            gradient.setColorAt(0.5, QColor('#3a3a40'))
            gradient.setColorAt(0.75, QColor('#4F46E5'))
            gradient.setColorAt(1, QColor('#3a3a40'))
            border_width = 3

        pen = QPen(QBrush(gradient), border_width)
        pen.setStyle(Qt.DashLine)
        pen.setDashPattern([8, 4])
        painter.setPen(pen)
        if self._is_drag_over:
            painter.setBrush(QColor(79, 70, 229, 30))
        else:
            painter.setBrush(QColor(26, 26, 29, 150))
        painter.drawRoundedRect(rect, 16, 16)
        painter.restore()

    def _draw_welcome_state(self, painter=None, rect=None):
        center_x = rect.center().x()
        y_offset = rect.top() + 50
        self._draw_upload_icon(painter, center_x, y_offset + 30, 60)

        font = QFont('Segoe UI', 20, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        heading_rect = QRectF(rect.left(), y_offset + 100, rect.width(), 40)
        painter.drawText(heading_rect, Qt.AlignCenter, tr('Drop Image Here'))

        font.setPointSize(13)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor('#a0a0a5'))
        sub_rect = QRectF(rect.left(), y_offset + 140, rect.width(), 30)
        painter.drawText(sub_rect, Qt.AlignCenter, tr('or click Open to browse files'))

        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor('#606065'))
        format_rect = QRectF(rect.left(), y_offset + 175, rect.width(), 25)
        painter.drawText(format_rect, Qt.AlignCenter, tr('Supports PNG, JPG, WebP, BMP, TIFF'))

    def _draw_drag_over_state(self, painter=None, rect=None):
        center_x = rect.center().x()
        center_y = rect.center().y()
        scale = 1 + self._pulse_value * 0.1
        self._draw_upload_icon(painter, center_x, center_y - 40, int(80 * scale), True)

        font = QFont('Segoe UI', 24, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        text_rect = QRectF(rect.left(), center_y + 50, rect.width(), 50)
        painter.drawText(text_rect, Qt.AlignCenter, tr('Release to Process'))

        font.setPointSize(14)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor('#818CF8'))
        sub_rect = QRectF(rect.left(), center_y + 95, rect.width(), 30)
        painter.drawText(sub_rect, Qt.AlignCenter, tr('AI will remove the background instantly'))

    def _draw_upload_icon(self, painter=None, x=None, y=None, size=60, highlighted=False):
        painter.save()
        if highlighted:
            color = QColor('#818CF8')
            glow_color = QColor(129, 140, 248, 100)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawEllipse(QPointF(x, y), size + 10, size + 10)
        else:
            color = QColor('#4F46E5')

        pen = QPen(color, 3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        half = size / 2
        frame_rect = QRectF(x - half, y - half, size, size)
        painter.drawRoundedRect(frame_rect, 8, 8)

        mountain_path = QPainterPath()
        mountain_path.moveTo((x - half) + 8, y + half - 12)
        mountain_path.lineTo((x - half) + size * 0.35, y - 5)
        mountain_path.lineTo((x - half) + size * 0.5, y + 8)
        mountain_path.lineTo((x - half) + size * 0.65, y - 10)
        mountain_path.lineTo(x + half - 8, y + half - 12)
        painter.drawPath(mountain_path)

        sun_x = x + half - 18
        sun_y = (y - half) + 18
        painter.drawEllipse(QPointF(sun_x, sun_y), 8, 8)

        arrow_y = y - half - 20
        painter.setPen(QPen(color, 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(x, arrow_y + 15), QPointF(x, arrow_y - 5))
        painter.drawLine(QPointF(x - 10, arrow_y + 5), QPointF(x, arrow_y - 5))
        painter.drawLine(QPointF(x + 10, arrow_y + 5), QPointF(x, arrow_y - 5))
        painter.restore()

    def _draw_active_stroke(self, painter=None):
        if not self._brush_points:
            return
        rect = self._get_image_rect()
        if not rect.isValid():
            return
        painter.save()
        if self._brush_is_add:
            stroke_color = QColor(34, 197, 94, 80)
        else:
            stroke_color = QColor(239, 68, 68, 80)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(stroke_color))
        radius = int(self._brush_radius * self._zoom)
        for img_x, img_y in self._brush_points:
            widget_x = rect.x() + img_x * self._zoom
            widget_y = rect.y() + img_y * self._zoom
            painter.drawEllipse(QPointF(widget_x, widget_y), radius, radius)
        painter.restore()

    def _draw_brush_cursor(self, painter=None):
        pos = self.mapFromGlobal(QCursor.pos())
        radius = int(self._brush_radius * self._zoom)
        pen = QPen(QColor('#ffffff'), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(pos, radius, radius)
        pen.setColor(QColor('#000000'))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawEllipse(pos, radius - 1, radius - 1)
        if self._brush_is_add:
            painter.setBrush(QColor('#22c55e'))
        else:
            painter.setBrush(QColor('#ef4444'))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(pos, 3, 3)

    def mousePressEvent(self, event=None):
        pos = event.position()
        self._last_mouse_pos = pos
        if self._view_mode == ViewMode.COMPARISON and self._is_over_slider(pos):
            self._is_dragging_slider = True
            return
        if event.button() == Qt.MiddleButton or self._current_tool == 'pan':
            self._is_panning = True
            self._update_cursor()
        elif event.button() == Qt.LeftButton:
            if self._original_pixmap is None:
                files, _ = QFileDialog.getOpenFileNames(
                    self,
                    tr('Select Images'),
                    '',
                    tr('Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif)')
                )
                if files:
                    if len(files) == 1:
                        self.file_dropped.emit(files[0])
                    else:
                        self.files_dropped.emit(files)
                return
            if self._current_tool == 'brush' and self._view_mode == ViewMode.SIDE_BY_SIDE:
                return
            img_x, img_y = self._widget_to_image(pos)
            if self._current_tool == 'brush':
                self._is_painting = True
                self._brush_points = [(img_x, img_y)]
        self.update()

    def mouseMoveEvent(self, event=None):
        pos = event.position()
        old_hover = self._slider_hover
        self._slider_hover = self._is_over_slider(pos)
        if old_hover != self._slider_hover:
            self._update_cursor()
        if self._is_dragging_slider:
            rect = self._get_image_rect()
            if rect.isValid():
                self._slider_position = (pos.x() - rect.x()) / rect.width()
                self._slider_position = max(0, min(1, self._slider_position))
            self.update()
            return
        if self._is_panning:
            delta = pos - self._last_mouse_pos
            self._pan_offset += delta
            self._last_mouse_pos = pos
            self.update()
            return
        if self._is_painting and self._current_tool == 'brush':
            if self._view_mode != ViewMode.SIDE_BY_SIDE:
                img_x, img_y = self._widget_to_image(pos)
                self._brush_points.append((img_x, img_y))
                self.update()
                return
        if self._current_tool == 'brush' or self._view_mode != ViewMode.SIDE_BY_SIDE:
            self.update()

    def mouseReleaseEvent(self, event=None):
        if self._is_dragging_slider:
            self._is_dragging_slider = False
        elif self._is_panning:
            self._is_panning = False
            self._update_cursor()
        elif self._is_painting and self._current_tool == 'brush':
            self._is_painting = False
            try:
                if len(self._brush_points) > 0:
                    self.brush_stroke.emit(self._brush_points, self._brush_radius, self._brush_is_add)
            finally:
                self._brush_points = []

    def mouseDoubleClickEvent(self, event=None):
        event.accept()

    def keyPressEvent(self, event=None):
        if event.key() == Qt.Key_Space:
            self.toggle_view()
        elif event.key() == Qt.Key_BracketLeft:
            self.set_brush_size(self._brush_radius - 5)
        elif event.key() == Qt.Key_BracketRight:
            self.set_brush_size(self._brush_radius + 5)
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key_0:
            self.zoom_fit()
        elif event.key() == Qt.Key_1:
            self.zoom_100()
        elif event.key() == Qt.Key_C:
            self.enable_comparison_slider()
        else:
            super().keyPressEvent(event)

    def event(self, event=None):
        event_type = event.type()
        if event_type == QEvent.Type.TouchBegin:
            self._handle_touch_begin(event)
            return True
        if event_type == QEvent.Type.TouchUpdate:
            self._handle_touch_update(event)
            return True
        if event_type == QEvent.Type.TouchEnd:
            self._handle_touch_end(event)
            return True
        return super().event(event)

    def _handle_touch_begin(self, event):
        points = event.points()
        for point in points:
            self._touch_points[point.id()] = point.position()
        if len(self._touch_points) == 2:
            positions = list(self._touch_points.values())
            delta = positions[0] - positions[1]
            self._initial_pinch_distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            self._initial_zoom = self._zoom

    def _handle_touch_update(self, event):
        points = event.points()
        for point in points:
            self._touch_points[point.id()] = point.position()
        if len(self._touch_points) == 1:
            delta = points[0].position() - points[0].lastPosition()
            self._pan_offset += delta
            self.update()
        elif len(self._touch_points) == 2:
            positions = list(self._touch_points.values())
            delta = positions[0] - positions[1]
            current_distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            if self._initial_pinch_distance > 0:
                scale = current_distance / self._initial_pinch_distance
                center = (positions[0] + positions[1]) / 2
                self._set_zoom(self._initial_zoom * scale, center)

    def _handle_touch_end(self, event):
        for point in event.points():
            self._touch_points.pop(point.id(), None)
        if len(self._touch_points) == 0:
            self._initial_pinch_distance = 0

    def resizeEvent(self, event=None):
        super().resizeEvent(event)
        if hasattr(self, '_checkerboard_timer'):
            self._checkerboard_timer.start()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.is_dir() or file_path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'):
                    event.acceptProposedAction()
                    self._is_drag_over = True
                    if hasattr(self, '_animation_timer') and not self._animation_timer.isActive():
                        self._animation_timer.start(30)
                    self.update()
                    return
                event.ignore()
                return

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.update()

    def dropEvent(self, event):
        self._is_drag_over = False
        self.update()
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.is_dir():
                    paths.extend(str(f) for f in p.rglob('*') if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'))
                elif p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'):
                    paths.append(str(p))
            if paths:
                if len(paths) == 1:
                    self.file_dropped.emit(paths[0])
                else:
                    self.files_dropped.emit(paths)
