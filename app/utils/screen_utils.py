from typing import Tuple
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QGuiApplication, QScreen


def get_screen_at(x: int, y: int) -> QScreen:
    """Returns the QScreen that contains the given coordinates, or primary screen."""
    point = QPoint(x, y)
    screen = QGuiApplication.screenAt(point)
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    return screen


def clamp_rect_to_screen(x: int, y: int, width: int, height: int, margin: int = 15) -> Tuple[int, int]:
    """Clamps a window rect (x, y, width, height) to strictly stay within the screen bounds."""
    screen = get_screen_at(x, y)
    if not screen:
        return x, y

    geo = screen.availableGeometry()

    min_x = geo.left() + margin
    max_x = geo.right() - width - margin
    min_y = geo.top() + margin
    max_y = geo.bottom() - height - margin

    # Ensure max bounds are valid even if window is larger than screen
    if max_x < min_x:
        max_x = min_x
    if max_y < min_y:
        max_y = min_y

    clamped_x = max(min_x, min(x, max_x))
    clamped_y = max(min_y, min(y, max_y))

    return clamped_x, clamped_y
