import math
import time
import threading
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import mouse

from app.config import config_manager
from app.utils.clipboard import get_selected_text_via_clipboard


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
                duration = up_time - self._down_time

                # 1. Intentional Drag selection (requires meaningful drag distance >= 14px and clear horizontal/vertical movement)
                is_drag_selection = (distance >= 14) and (abs(dx) >= 10 or abs(dy) >= 10)

                # 2. Word selection via double click (little or no movement)
                is_double_click_selection = (self._click_count == 2) and (distance < 8)

                if is_drag_selection or is_double_click_selection:
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
