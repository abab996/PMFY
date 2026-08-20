from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
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
from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect

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
        self._diameter: int = 34
        self._padding: int = 8  # for shadow
        self.setFixedSize(self._diameter + self._padding * 2, self._diameter + self._padding * 2)

        # Auto-hide timer if user ignores the bubble
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_smoothly)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def show_at_selection(self, text: str, x: int = 0, y: int = 0):
        """Displays the blue circle right beside the mouse selection in Qt logical coords."""
        self._text = text
        self._is_hovered = False

        # Query exact cursor position in Qt logical coordinates
        cursor_pos = QCursor.pos()
        raw_x = cursor_pos.x() + 10
        raw_y = cursor_pos.y() + 10

        # Clamp strictly inside current screen bounds
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
        self._hide_timer.stop()
        self.hide()

    def enterEvent(self, event):
        """Triggered automatically when the mouse hovers over the blue circle."""
        self._is_hovered = True
        self._hide_timer.stop()
        self.update()

        # Emit translation trigger in Qt logical coords
        cursor_pos = QCursor.pos()
        self.hover_triggered.emit(self._text, cursor_pos.x(), cursor_pos.y())

        # Hide bubble as translation popup will open
        self.hide()
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

        # Draw "译" icon / Symbol inside
        painter.setPen(QColor(255, 255, 255, 245))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)
        painter.drawText(
            QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2),
            Qt.AlignmentFlag.AlignCenter,
            "译",
        )
