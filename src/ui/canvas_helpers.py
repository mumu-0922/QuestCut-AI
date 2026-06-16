"""Small geometry helpers for CanvasWidget."""
from PySide6.QtCore import QPointF, QRectF, QSize


def fit_zoom(image_size: QSize, view_size: QSize, *, margin: float = 0.95) -> float:
    """Return a fit-to-view zoom value, falling back to 1 for invalid sizes."""
    if image_size.width() <= 0 or image_size.height() <= 0:
        return 1
    if view_size.width() <= 0 or view_size.height() <= 0:
        return 1
    return min(view_size.width() / image_size.width(), view_size.height() / image_size.height()) * margin


def image_rect(widget_size: QSize, pixmap_size: QSize, zoom: float, pan_offset: QPointF) -> QRectF:
    """Return the target rect for an image centered in a widget."""
    scaled_width = pixmap_size.width() * zoom
    scaled_height = pixmap_size.height() * zoom
    center = QPointF(widget_size.width() / 2, widget_size.height() / 2)
    x = center.x() + pan_offset.x() - scaled_width / 2
    y = center.y() + pan_offset.y() - scaled_height / 2
    return QRectF(x, y, scaled_width, scaled_height)
