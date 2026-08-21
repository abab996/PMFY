import os
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import config_manager
from app.core.ai_client import ai_client, PROMPT_PRESETS
from app.core.tts_engine import tts_engine
from app.core.ocr_engine import ocr_engine
from app.core.screen_capture import screen_capture
from app.utils.screen_utils import clamp_rect_to_screen


class TestPMFYCore(unittest.TestCase):

    def test_01_config_manager(self):
        """Test configuration reading, updating, and persistence."""
        val = config_manager.get("fullscreen", "hotkey")
        self.assertEqual(val, "Ctrl+Win+Alt")

        # Test deep update
        config_manager.set("translation", "target_language", "zh-CN")
        self.assertEqual(config_manager.get("translation", "target_language"), "zh-CN")

        # Test max_concurrency config
        config_manager.set("api", "max_concurrency", 3)
        self.assertEqual(config_manager.get("api", "max_concurrency"), 3)

    def test_02_tts_and_phonetics(self):
        """Test IPA and Pinyin extraction."""
        # English phonetic IPA
        ipa_res = tts_engine.get_phonetic_or_pinyin("hello")
        self.assertTrue(bool(ipa_res), f"Expected IPA for hello, got: {ipa_res}")
        self.assertTrue(ipa_res.startswith("/") and ipa_res.endswith("/"), f"IPA format check: {ipa_res}")

        # Chinese Pinyin
        py_res = tts_engine.get_phonetic_or_pinyin("你好世界")
        self.assertTrue("nǐ" in py_res and "hǎo" in py_res, f"Pinyin check: {py_res}")

    def test_03_ai_client_parser_and_presets(self):
        """Test AI client robust response parser and prompt presets."""
        mock_raw_json = """
        ```json
        {
          "translation": "你好，世界",
          "phonetic": "/həˈloʊ wɜːld/",
          "explanation": "常用问候语，用于向全世界打招呼。",
          "examples": [
            {"src": "Hello world! This is a test.", "dst": "你好世界！这是一个测试。"}
          ]
        }
        ```
        """
        parsed = ai_client._parse_json_result(mock_raw_json, "Hello world")
        self.assertFalse(parsed["error"])
        self.assertEqual(parsed["translation"], "你好，世界")
        self.assertEqual(parsed["phonetic"], "/həˈloʊ wɜːld/")
        self.assertTrue(len(parsed["examples"]) == 1)

        # Test broken JSON with unescaped quotes inside string
        broken_json = '''```json
{
  "translation": "即可即刻体验！",
  "phonetic": "jí kě jí kè tǐ yàn",
  "explanation": "即可：副词，意为"就可以、便能够"；即刻：副词，意为"立刻、马上"。句中两个时间副词连用，起到强调作用，突出动作的即时性和便捷性，常用于广告或营销语境。体验：动词，指亲身感受或尝试某事物。整体句式简洁有力，富有号召力。",
  "examples": [
    {
      "src": "即可即刻体验！",
      "dst": "即可即刻体验！"
    }
  ]
}
```'''
        parsed_broken = ai_client._parse_json_result(broken_json, "即可即刻体验！")
        self.assertFalse(parsed_broken["error"])
        self.assertEqual(parsed_broken["translation"], "即可即刻体验！")
        self.assertEqual(parsed_broken["phonetic"], "jí kě jí kè tǐ yàn")
        self.assertTrue("即可：副词" in parsed_broken["explanation"])

        # Check prompt presets
        self.assertIn("academic", PROMPT_PRESETS)
        self.assertIn("tech", PROMPT_PRESETS)
        self.assertIn("game", PROMPT_PRESETS)

        # Check semaphore
        sem = ai_client._get_semaphore()
        self.assertIsNotNone(sem)

    def test_04_screen_utils_clamping(self):
        """Test screen boundary clamping logic."""
        from PyQt6.QtWidgets import QApplication
        qapp = QApplication.instance() or QApplication(sys.argv)

        cx, cy = clamp_rect_to_screen(99999, 99999, 400, 300, margin=15)
        self.assertLess(cx, 99999)
        self.assertLess(cy, 99999)

        cx_neg, cy_neg = clamp_rect_to_screen(-1000, -1000, 400, 300, margin=15)
        self.assertGreaterEqual(cx_neg, 0)
        self.assertGreaterEqual(cy_neg, 0)

    def test_05_ocr_and_image_rendering(self):
        """Test OCR detection and in-place image rendering."""
        img = Image.new("RGB", (400, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "Welcome to Translation", fill=(0, 0, 0))
        draw.text((20, 80), "Powerful AI Desktop Tool", fill=(0, 0, 0))

        blocks = ocr_engine.recognize(img)
        self.assertIsInstance(blocks, list)

        translated_texts = ["欢迎使用翻译", "强大的 AI 桌面工具"]
        rendered_img = screen_capture.render_inplace_translation(img, blocks, translated_texts)
        self.assertEqual(rendered_img.size, (400, 150))
        self.assertEqual(rendered_img.mode, "RGB")

    def test_06_ui_instantiation(self):
        """Test that all PyQt6 and Fluent widgets instantiate without errors."""
        from PyQt6.QtWidgets import QApplication
        from app.ui.settings_window import SettingsWindow
        from app.ui.selection_bubble import SelectionBubble
        from app.ui.translation_popup import TranslationPopup
        from app.ui.fullscreen_viewer import FullscreenViewer
        from app.ui.radial_menu import RadialMenuWindow
        from app.ui.area_snipping import AreaSnippingWindow
        from app.ui.input_translation_window import InputTranslationWindow
        from app.ui.ask_ai_window import AskAIWindow, get_ask_ai_window
        from app.ui.tray_icon import SystemTray

        qapp = QApplication.instance() or QApplication(sys.argv)

        settings = SettingsWindow()
        self.assertIsNotNone(settings)

        bubble = SelectionBubble()
        self.assertIsNotNone(bubble)

        popup = TranslationPopup()
        self.assertIsNotNone(popup)

        viewer = FullscreenViewer()
        self.assertIsNotNone(viewer)

        radial = RadialMenuWindow()
        self.assertIsNotNone(radial)

        area = AreaSnippingWindow()
        self.assertIsNotNone(area)

        input_win = InputTranslationWindow()
        self.assertIsNotNone(input_win)

        ask_ai = get_ask_ai_window()
        self.assertIsNotNone(ask_ai)

        # Test AskAI repeated context loading and complete message clearing
        from app.ui.ask_ai_window import MessageBubble
        ask_ai.set_context("Hello world 1", "你好世界 1")
        ask_ai.set_context("Hello world 2", "你好世界 2")
        ask_ai.set_context("Hello world 3", "你好世界 3")
        self.assertEqual(len(ask_ai.messages_container.findChildren(MessageBubble)), 1)

        ask_ai._append_message("用户提问测试", is_user=True)
        ask_ai._append_message("### AI 回答\n- 条目1\n- 条目2", is_user=False)
        self.assertEqual(len(ask_ai.messages_container.findChildren(MessageBubble)), 3)

        ask_ai.clear_conversation(show_welcome=True)
        self.assertEqual(len(ask_ai.messages_container.findChildren(MessageBubble)), 1)

        tray = SystemTray()
        self.assertIsNotNone(tray)
        print("[Test] All UI components, RadialMenu, AreaSnipping, and InputTranslationWindow instantiated successfully!")

    def test_07_autostart_and_bubble_settings(self):
        """Test autostart detection and dynamic selection bubble sizing."""
        from PyQt6.QtWidgets import QApplication
        from app.utils.autostart import is_autostart_enabled, get_launch_command
        from app.ui.selection_bubble import SelectionBubble

        qapp = QApplication.instance() or QApplication(sys.argv)

        cmd = get_launch_command()
        self.assertTrue(len(cmd) > 0)

        # Check autostart read without crashing
        status = is_autostart_enabled()
        self.assertIsInstance(status, bool)

        # Check dynamic bubble configuration
        config_manager.set("selection", "circle_size", 40)
        config_manager.set("selection", "hover_delay", 0.25)

        bubble = SelectionBubble()
        bubble.reload_config()
        self.assertEqual(bubble._diameter, 40)
        self.assertEqual(bubble._hover_delay, 0.25)
        self.assertEqual(bubble.width(), 40 + 16)

    def test_08_window_utils_and_console_safety(self):
        """Test window inspection, non-client hit-test constants, and terminal Ctrl+C safety shields."""
        from app.utils.window_utils import (
            HTCLIENT,
            HTCAPTION,
            HTBORDER,
            is_console_window,
            get_window_info_at,
            get_window_rect,
            CONSOLE_CLASS_NAMES,
            SHELL_CLASS_NAMES,
        )
        from app.utils.clipboard import get_selected_text_via_clipboard
        from app.core.mouse_hook import mouse_hook

        # Check constants
        self.assertEqual(HTCLIENT, 1)
        self.assertEqual(HTCAPTION, 2)
        self.assertIn("ConsoleWindowClass", CONSOLE_CLASS_NAMES)
        self.assertIn("CASCADIA_HOSTING_WINDOW_CLASS", CONSOLE_CLASS_NAMES)
        self.assertIn("Shell_TrayWnd", SHELL_CLASS_NAMES)

        # Check non-crashing window queries
        info = get_window_info_at(0, 0)
        self.assertEqual(len(info), 5)

        # Check mouse hook is instantiated
        self.assertIsNotNone(mouse_hook)


if __name__ == "__main__":
    unittest.main()
