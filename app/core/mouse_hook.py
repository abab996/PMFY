import math
import time
import threading
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import mouse

from app.config import config_manager
from app.utils.clipboard import get_selected_text_via_clipboard
from app.utils.window_utils import (
    HTCLIENT,
    SHELL_CLASS_NAMES,
    get_window_info_at,
    get_window_rect,
)


class MouseHook(QObject):
    """Global mouse listener that detects intentional text selection actions (drag or double-click)."""

    # Emits (selected_text: str, cursor_x: int, cursor_y: int)
    selection_detected = pyqtSignal(str, int, int)
    mouse_clicked = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self._listener: Optional[mouse.Listener] = None
        self._down_pos = (0, 0)
        self._down_time = 0.0
        self._is_pressed = False
        self._enabled = True

        self._last_click_time = 0.0
        self._last_click_pos = (0, 0)
        self._click_count = 1

        # Window & Non-client hit-test tracking
        self._down_root_hwnd = 0
        self._down_class_name = ""
        self._down_window_rect = None
        self._down_hit_test = HTCLIENT

    def start(self):
        if self._listener is None:
            self._listener = mouse.Listener(
                on_click=self._on_click,
            )
            self._listener.daemon = True
            self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        if not self._enabled:
            return

        # Check if selection translation is enabled in config
        if not config_manager.get("selection", "enabled", True):
            return

        if button == mouse.Button.left:
            now = time.time()
            if pressed:
                self._down_pos = (x, y)
                self._down_time = now
                self._is_pressed = True

                # Inspect window under cursor at mouse down
                _, root_hwnd, cls_name, rect, hit_test = get_window_info_at(x, y)
                self._down_root_hwnd = root_hwnd
                self._down_class_name = cls_name
                self._down_window_rect = rect
                self._down_hit_test = hit_test

                # Check for double-click
                time_diff = now - self._last_click_time
                dist_from_last = math.hypot(x - self._last_click_pos[0], y - self._last_click_pos[1])
                if time_diff < 0.35 and dist_from_last < 8:
                    self._click_count = 2
                else:
                    self._click_count = 1

                self._last_click_time = now
                self._last_click_pos = (x, y)
                self.mouse_clicked.emit(int(x), int(y))
            else:
                if not self._is_pressed:
                    return
                self._is_pressed = False
                up_pos = (x, y)
                up_time = now

                dx = up_pos[0] - self._down_pos[0]
                dy = up_pos[1] - self._down_pos[1]
                distance = math.hypot(dx, dy)

                # 1. Intentional Drag selection (requires meaningful drag distance >= 14px and clear horizontal/vertical movement)
                is_drag_selection = (distance >= 14) and (abs(dx) >= 10 or abs(dy) >= 10)

                # 2. Word selection via double click (little or no movement)
                is_double_click_selection = (self._click_count == 2) and (distance < 8)

                if is_drag_selection or is_double_click_selection:
                    # Filter A: If mouse was pressed on non-client area (Title bar, caption, border, scrollbar, window buttons)
                    if is_drag_selection and self._down_hit_test != HTCLIENT:
                        return

                    # Filter B: Inspect window at mouse release
                    _, up_root_hwnd, up_cls_name, _, up_hit_test = get_window_info_at(x, y)
                    if is_drag_selection and up_hit_test != HTCLIENT:
                        return

                    # Filter C: If dragging crossed different top-level root windows
                    if is_drag_selection and self._down_root_hwnd != up_root_hwnd:
                        return

                    # Filter D: If the window itself moved or was resized during the drag (e.g. dragging CMD/Terminal/App window)
                    current_rect = get_window_rect(self._down_root_hwnd)
                    if is_drag_selection and current_rect and self._down_window_rect and current_rect != self._down_window_rect:
                        return

                    # Filter E: If mouse was on desktop background or taskbar icons
                    if self._down_class_name in SHELL_CLASS_NAMES or up_cls_name in SHELL_CLASS_NAMES:
                        return

                    threading.Thread(
                        target=self._check_selection_text,
                        args=(int(up_pos[0]), int(up_pos[1])),
                        daemon=True
                    ).start()

    def _check_selection_text(self, x: int, y: int):
        time.sleep(0.06)  # Short pause to let OS update selection
        text = get_selected_text_via_clipboard(timeout=0.15)
        if text and len(text.strip()) >= 1:
            # Emit signal to Qt main thread
            self.selection_detected.emit(text.strip(), x, y)


mouse_hook = MouseHook()
