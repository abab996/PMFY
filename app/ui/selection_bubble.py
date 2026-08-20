from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from app.config import config_manager
from app.utils.screen_utils import clamp_rect_to_screen


class SelectionBubble(QWidget):
    """Floating blue circle trigger that appears near text selections without stealing focus."""

    # Emits (selected_text: str, trigger_x: int, trigger_y: int)
    hover_triggered = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._text: str = ""
        self._is_hovered: bool = False
        self._diameter: int = 32
        self._padding: int = 8
        self._hover_delay: float = 0.15

        # Auto-hide timer if user ignores the bubble
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_smoothly)

        # Hover activation timer
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._on_hover_timer_fired)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reload_config()

    def reload_config(self):
        """Reloads circle size, padding and hover delay dynamically."""
        self._diameter = int(config_manager.get("selection", "circle_size", 32))
        self._hover_delay = float(config_manager.get("selection", "hover_delay", 0.15))
        total_size = self._diameter + self._padding * 2
        self.setFixedSize(total_size, total_size)

    def show_at_selection(self, text: str, x: int = 0, y: int = 0):
        """Displays the blue circle right beside the mouse selection in Qt logical coords."""
        self.reload_config()
        self._text = text
        self._is_hovered = False
        self._hover_timer.stop()

        cursor_pos = QCursor.pos()
        raw_x = cursor_pos.x() + 10
        raw_y = cursor_pos.y() + 10

        clamped_x, clamped_y = clamp_rect_to_screen(
            raw_x, raw_y, self.width(), self.height(), margin=16
        )

        self.move(clamped_x, clamped_y)
        self.show()
        self.raise_()

        # Start 4.5s auto-hide countdown
        self._hide_timer.start(4500)
        self.update()

    def hide_smoothly(self):
        self._hover_timer.stop()
        self._hide_timer.stop()
        self.hide()

    def enterEvent(self, event):
        """Triggered when the mouse enters the blue circle: starts hover delay countdown."""
        self._is_hovered = True
        self._hide_timer.stop()
        self.update()

        # Start hover delay timer (e.g. 150ms)
        delay_ms = max(10, int(self._hover_delay * 1000))
        self._hover_timer.start(delay_ms)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Triggered if mouse leaves before hover timer fires."""
        self._is_hovered = False
        self._hover_timer.stop()
        self._hide_timer.start(2500)
        self.update()
        super().leaveEvent(event)

    def _on_hover_timer_fired(self):
        cursor_pos = QCursor.pos()
        self.hover_triggered.emit(self._text, cursor_pos.x(), cursor_pos.y())
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._hover_timer.stop()
            cursor_pos = QCursor.pos()
            self.hover_triggered.emit(self._text, cursor_pos.x(), cursor_pos.y())
            self.hide()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        radius = (self._diameter / 2.0) + (2.0 if self._is_hovered else 0.0)

        # Draw soft outer glow / shadow
        shadow_path = QPainterPath()
        shadow_path.addEllipse(QPointF(center_x, center_y + 2), radius + 2, radius + 2)
        painter.fillPath(shadow_path, QColor(0, 120, 212, 60))

        # Circle Gradient: Modern Windows 11 Blue
        gradient = QLinearGradient(0, center_y - radius, 0, center_y + radius)
        if self._is_hovered:
            gradient.setColorAt(0.0, QColor("#1E90FF"))
            gradient.setColorAt(1.0, QColor("#0078D4"))
        else:
            gradient.setColorAt(0.0, QColor("#0078D4"))
            gradient.setColorAt(1.0, QColor("#005FB8"))

        circle_path = QPainterPath()
        circle_path.addEllipse(QPointF(center_x, center_y), radius, radius)

        # Fill background
        painter.fillPath(circle_path, QBrush(gradient))

        # Outer subtle border
        border_pen = QPen(QColor(255, 255, 255, 180), 1.2)
        painter.setPen(border_pen)
        painter.drawPath(circle_path)

        # Draw "译" icon / Symbol inside with dynamically scaled font size
        painter.setPen(QColor(255, 255, 255, 245))
        font_size = max(8, int(self._diameter * 0.36))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)
        painter.drawText(
            QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2),
            Qt.AlignmentFlag.AlignCenter,
            "译",
        )
