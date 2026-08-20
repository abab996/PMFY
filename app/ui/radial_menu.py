import math
from typing import Optional

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

from app.config import config_manager
from app.ui.theme import ACCENT_COLOR
from app.utils.screen_utils import clamp_rect_to_screen


class RadialMenuWindow(QWidget):
    """Sleek Windows 11 Acrylic Pie / Radial Menu at Cursor Position."""

    action_fullscreen = pyqtSignal()
    action_area = pyqtSignal()
    action_toggle_instant = pyqtSignal()
    action_input_translation = pyqtSignal()
    action_cancelled = pyqtSignal()

    SIZE = 240
    RADIUS = 120
    CENTER_RADIUS = 38

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.SIZE, self.SIZE)

        self._active_zone = "CENTER"  # "TOP", "BOTTOM", "LEFT", "RIGHT", "CENTER", "NONE"
        self._center_screen_pos = QPoint(0, 0)

        # Polling timer for mouse cursor position relative to radial center
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._poll_cursor)

    def show_at_cursor(self):
        """Displays radial menu centered directly at the mouse cursor position."""
        cursor_pos = QCursor.pos()
        self._center_screen_pos = cursor_pos

        target_x = cursor_pos.x() - self.RADIUS
        target_y = cursor_pos.y() - self.RADIUS

        clamped_x, clamped_y = clamp_rect_to_screen(
            target_x, target_y, self.SIZE, self.SIZE, margin=10
        )
        self.move(clamped_x, clamped_y)

        self._active_zone = "CENTER"
        self.show()
        self.raise_()
        self._timer.start()
        self.update()

    def trigger_selected_action(self):
        """Called when hotkey is released to execute the currently hovered sector action."""
        self._timer.stop()
        self.hide()

        zone = self._active_zone
        if zone == "TOP":
            self.action_fullscreen.emit()
        elif zone == "BOTTOM":
            self.action_area.emit()
        elif zone == "LEFT":
            self.action_toggle_instant.emit()
        elif zone == "RIGHT":
            self.action_input_translation.emit()
        else:
            self.action_cancelled.emit()

    def _poll_cursor(self):
        cursor_pos = QCursor.pos()
        local_x = cursor_pos.x() - self.x()
        local_y = cursor_pos.y() - self.y()

        dx = local_x - self.RADIUS
        dy = local_y - self.RADIUS
        distance = math.hypot(dx, dy)

        if distance <= self.CENTER_RADIUS:
            new_zone = "CENTER"
        elif distance > self.RADIUS + 30:
            new_zone = "NONE"
        else:
            angle_deg = math.degrees(math.atan2(dy, dx))  # -180 to 180
            if -135 <= angle_deg < -45:
                new_zone = "TOP"
            elif 45 <= angle_deg < 135:
                new_zone = "BOTTOM"
            elif -45 <= angle_deg < 45:
                new_zone = "RIGHT"
            else:
                new_zone = "LEFT"

        if new_zone != self._active_zone:
            self._active_zone = new_zone
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        cx, cy = self.RADIUS, self.RADIUS
        outer_r = self.RADIUS - 4
        center_r = self.CENTER_RADIUS

        instant_on = config_manager.get("selection", "instant_mode", False)

        # Base Colors
        bg_color = QColor(24, 24, 27, 235)
        active_color = QColor(0, 120, 212, 235)  # Win11 Accent Blue
        border_color = QColor(255, 255, 255, 45)
        text_dim = QColor(220, 220, 225)
        text_active = QColor(255, 255, 255)

        # 1. Draw 4 Pie Sectors
        # Sectors: TOP (angle -135 to -45), RIGHT (-45 to 45), BOTTOM (45 to 135), LEFT (135 to 225)
        sectors = [
            ("TOP", -135, 90, "🖥️\n全屏翻译", 0, -58),
            ("RIGHT", -45, 90, "✍️\n输入翻译", 58, 0),
            ("BOTTOM", 45, 90, "✂️\n选区翻译", 0, 58),
            ("LEFT", 135, 90, f"⚡\n立即翻译\n({'开' if instant_on else '关'})", -58, 0),
        ]

        rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        for name, start_angle, span_angle, label_text, tx, ty in sectors:
            is_active = (self._active_zone == name)
            fill_color = active_color if is_active else bg_color

            path = QPainterPath()
            path.arcMoveTo(rect, -start_angle)
            path.arcTo(rect, -start_angle, -span_angle)
            path.lineTo(cx, cy)
            path.closeSubpath()

            painter.setPen(QPen(border_color, 1.2))
            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path)

            # Draw Label
            painter.setPen(text_active if is_active else text_dim)
            font = QFont("Segoe UI", 10 if is_active else 9, QFont.Weight.Bold if is_active else QFont.Weight.Medium)
            painter.setFont(font)

            text_rect = QRectF(cx + tx - 45, cy + ty - 24, 90, 48)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label_text)

        # 2. Draw Center Circle (Cancel)
        is_center_active = (self._active_zone == "CENTER")
        center_fill = QColor(216, 59, 1, 230) if is_center_active else QColor(36, 36, 40, 245)

        painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
        painter.setBrush(QBrush(center_fill))
        painter.drawEllipse(QPoint(cx, cy), center_r, center_r)

        # Center Text
        painter.setPen(QColor(255, 255, 255))
        font_c = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_c)
        c_rect = QRectF(cx - center_r, cy - center_r, center_r * 2, center_r * 2)
        painter.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, "✕\n取消")
