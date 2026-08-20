import threading
import time
from typing import Callable, Dict, Optional, Set

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

from app.config import config_manager


class HotkeyManager(QObject):
    """Manages global hotkeys, including radial menu hold/release and standalone triggers."""

    radial_hotkey_pressed = pyqtSignal()
    radial_hotkey_released = pyqtSignal()
    area_hotkey_triggered = pyqtSignal()
    input_hotkey_triggered = pyqtSignal()
    fullscreen_hotkey_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_keys: Set[keyboard.Key] = set()
        self._listener: Optional[keyboard.Listener] = None

        self._radial_hotkey_str = "Ctrl+Win+Alt"
        self._area_hotkey_str = ""
        self._input_hotkey_str = ""
        self._fullscreen_hotkey_str = ""

        self._radial_is_active = False
        self._last_radial_trigger_time = 0.0

        self._area_pressed = False
        self._input_pressed = False
        self._fullscreen_pressed = False

    def start(self):
        self.reload_hotkeys()
        if self._listener is None:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def reload_hotkeys(self):
        hotkeys_cfg = config_manager.get("hotkeys", default={})
        self._radial_hotkey_str = hotkeys_cfg.get("radial_menu", "Ctrl+Win+Alt")
        self._area_hotkey_str = hotkeys_cfg.get("area_snipping", "")
        self._input_hotkey_str = hotkeys_cfg.get("input_translation", "")
        self._fullscreen_hotkey_str = hotkeys_cfg.get("fullscreen", "")

    def _normalize_key(self, key):
        if isinstance(key, keyboard.Key):
            return key.name.lower()
        elif hasattr(key, "char") and key.char:
            return key.char.lower()
        return str(key).lower()

    def _on_press(self, key):
        self._current_keys.add(key)
        self._check_matches()

    def _on_release(self, key):
        self._current_keys.discard(key)
        key_names = {self._normalize_key(k) for k in self._current_keys}

        # Check if radial hotkey was released
        if self._radial_is_active:
            if not self._is_match(self._radial_hotkey_str, key_names):
                self._radial_is_active = False
                self.radial_hotkey_released.emit()

        # Reset standalone flags
        if self._area_hotkey_str and not self._is_match(self._area_hotkey_str, key_names):
            self._area_pressed = False
        if self._input_hotkey_str and not self._is_match(self._input_hotkey_str, key_names):
            self._input_pressed = False
        if self._fullscreen_hotkey_str and not self._is_match(self._fullscreen_hotkey_str, key_names):
            self._fullscreen_pressed = False

    def _is_match(self, hotkey_str: str, key_names: Set[str]) -> bool:
        if not hotkey_str or not hotkey_str.strip():
            return False
        tokens = [t.strip().lower() for t in hotkey_str.split("+")]

        def match_token(token):
            if token in ("ctrl", "control"):
                return any("ctrl" in k for k in key_names)
            elif token in ("win", "cmd", "super"):
                return any("cmd" in k or "win" in k for k in key_names)
            elif token in ("alt", "menu"):
                return any("alt" in k for k in key_names)
            elif token in ("shift",):
                return any("shift" in k for k in key_names)
            else:
                return token in key_names

        return all(match_token(t) for t in tokens)

    def _check_matches(self):
        key_names = {self._normalize_key(k) for k in self._current_keys}
        now = time.time()

        # 1. Check Radial Menu Hotkey
        if self._is_match(self._radial_hotkey_str, key_names):
            if not self._radial_is_active and (now - self._last_radial_trigger_time > 0.3):
                self._radial_is_active = True
                self._last_radial_trigger_time = now
                self.radial_hotkey_pressed.emit()

        # 2. Check Area Snipping Hotkey
        if self._area_hotkey_str and self._is_match(self._area_hotkey_str, key_names):
            if not self._area_pressed:
                self._area_pressed = True
                self.area_hotkey_triggered.emit()

        # 3. Check Input Translation Hotkey
        if self._input_hotkey_str and self._is_match(self._input_hotkey_str, key_names):
            if not self._input_pressed:
                self._input_pressed = True
                self.input_hotkey_triggered.emit()

        # 4. Check Standalone Fullscreen Hotkey
        if self._fullscreen_hotkey_str and self._is_match(self._fullscreen_hotkey_str, key_names):
            if not self._fullscreen_pressed:
                self._fullscreen_pressed = True
                self.fullscreen_hotkey_triggered.emit()


hotkey_manager = HotkeyManager()
