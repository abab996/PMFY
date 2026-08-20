import sys
from typing import Optional

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QIcon, QGuiApplication
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from app.config import config_manager
from app.core.hotkey_manager import hotkey_manager
from app.core.mouse_hook import mouse_hook
from app.ui.area_snipping import AreaSnippingWindow
from app.ui.fullscreen_viewer import FullscreenViewer
from app.ui.input_translation_window import InputTranslationWindow
from app.ui.radial_menu import RadialMenuWindow
from app.ui.selection_bubble import SelectionBubble
from app.ui.settings_window import SettingsWindow
from app.ui.translation_popup import TranslationPopup
from app.ui.tray_icon import SystemTray, create_tray_icon_pixmap


class PMFYApplication(QObject):
    """Main Application Coordinator for PMFY Global Translation."""

    def __init__(self, qapp: QApplication):
        super().__init__()
        self.qapp = qapp

        # Initialize UI Components
        self.settings_window = SettingsWindow()
        self.selection_bubble = SelectionBubble()
        self.translation_popup = TranslationPopup()
        self.fullscreen_viewer = FullscreenViewer()
        self.radial_menu = RadialMenuWindow()
        self.area_snipping = AreaSnippingWindow()
        self.input_translation_window = InputTranslationWindow()
        self.tray_icon = SystemTray()

        self._connect_signals()
        self._start_services()

    def _connect_signals(self):
        # 1. Mouse Hook -> Selection Bubble / Instant Popup
        mouse_hook.selection_detected.connect(self._on_text_selected)
        mouse_hook.mouse_clicked.connect(self._on_mouse_clicked)

        # 2. Selection Bubble Hover -> Translation Popup
        self.selection_bubble.hover_triggered.connect(self._on_bubble_hovered)

        # 3. Global Hotkeys
        hotkey_manager.radial_hotkey_pressed.connect(self.radial_menu.show_at_cursor)
        hotkey_manager.radial_hotkey_released.connect(self.radial_menu.trigger_selected_action)

        hotkey_manager.area_hotkey_triggered.connect(self.area_snipping.start_snipping)
        hotkey_manager.input_hotkey_triggered.connect(self.input_translation_window.show_window)
        hotkey_manager.fullscreen_hotkey_triggered.connect(self.fullscreen_viewer.start_fullscreen_translation)

        # 4. Radial Menu Actions
        self.radial_menu.action_fullscreen.connect(self.fullscreen_viewer.start_fullscreen_translation)
        self.radial_menu.action_area.connect(self.area_snipping.start_snipping)
        self.radial_menu.action_toggle_instant.connect(self._on_toggle_instant_mode)
        self.radial_menu.action_input_translation.connect(self.input_translation_window.show_window)

        # 5. Area Snipping & Fullscreen Detail Translation -> Translation Popup
        self.area_snipping.detail_translate_requested.connect(self._on_detail_translate_requested)
        self.fullscreen_viewer.detail_translate_requested.connect(self._on_detail_translate_requested)

        # 6. System Tray Actions
        self.tray_icon.open_settings_requested.connect(self.show_settings)
        self.tray_icon.fullscreen_translate_requested.connect(self.fullscreen_viewer.start_fullscreen_translation)
        self.tray_icon.selection_toggled.connect(self._on_selection_toggled)
        self.tray_icon.exit_requested.connect(self.exit_app)

        # 7. Settings saved
        self.settings_window.settings_saved.connect(self._on_settings_saved)

    def _start_services(self):
        # Show Tray Icon
        self.tray_icon.show()

        # Start Global Listeners
        mouse_hook.start()
        hotkey_manager.start()

        # If API key is empty, open settings automatically to guide user
        api_key = config_manager.get("api", "api_key", "").strip()
        if not api_key:
            QTimer.singleShot(600, self.show_settings)
            self.tray_icon.showMessage(
                "PMFY 全局翻译",
                "欢迎使用 PMFY！请先在设置中配置您的 OpenAI 或 Anthropic API Key。",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
        else:
            self.tray_icon.showMessage(
                "PMFY 全局翻译",
                "软件已就绪！按住快捷键 (Ctrl+Win+Alt) 呼出轮盘，松开即刻执行功能。",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_text_selected(self, text: str, x: int, y: int):
        # Ignore if selection translation disabled
        if not config_manager.get("selection", "enabled", True):
            return

        # Suppress floating bubble if fullscreen viewer or area snipping is active
        if self.fullscreen_viewer.isVisible() or self.area_snipping.isVisible():
            return

        # Instant mode: directly show translation popup without hovering bubble
        if config_manager.get("selection", "instant_mode", False):
            self.translation_popup.show_translation(text, x, y)
        else:
            self.selection_bubble.show_at_selection(text, x, y)

    def _on_bubble_hovered(self, text: str, x: int, y: int):
        self.translation_popup.show_translation(text, x, y)

    def _on_mouse_clicked(self, x: int, y: int):
        if self.selection_bubble.isVisible():
            geo = self.selection_bubble.geometry()
            if not geo.contains(x, y):
                self.selection_bubble.hide()

    def _on_toggle_instant_mode(self):
        cur_mode = config_manager.get("selection", "instant_mode", False)
        new_mode = not cur_mode
        config_manager.set("selection", "instant_mode", new_mode)
        status_msg = "已开启 (划词直接弹出翻译卡片)" if new_mode else "已关闭 (恢复蓝色悬浮球)"
        self.tray_icon.showMessage(
            "PMFY 划词模式切换",
            f"⚡ 立即翻译模式：{status_msg}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _on_detail_translate_requested(self, text: str, pos_x: int, pos_y: int):
        self.translation_popup.show_translation(text, pos_x, pos_y)

    def _on_selection_toggled(self, enabled: bool):
        mouse_hook.set_enabled(enabled)

    def _on_settings_saved(self):
        hotkey_manager.reload_hotkeys()

        sel_enabled = config_manager.get("selection", "enabled", True)
        mouse_hook.set_enabled(sel_enabled)
        self.tray_icon.act_sel_toggle.setChecked(sel_enabled)

    def show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def exit_app(self):
        mouse_hook.stop()
        hotkey_manager.stop()
        self.tray_icon.hide()
        self.qapp.quit()
