import threading
from typing import Any, Dict, Optional

from PyQt6.QtCore import (
    QPoint,
    QRect,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QIcon,
    QGuiApplication,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ComboBox

from app.config import config_manager
from app.core.ai_client import ai_client
from app.core.tts_engine import tts_engine
from app.ui.ask_ai_window import get_ask_ai_window
from app.ui.theme import ACCENT_COLOR
from app.utils.screen_utils import clamp_rect_to_screen


class TranslationPopup(QWidget):
    """Modern Windows 11 Fluent Design Translation Result Popup with Instant Lang Switch & Ask AI."""

    translation_finished = pyqtSignal(dict)
    translation_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._current_text: str = ""
        self._current_phonetic: str = ""
        self._current_trans: str = ""
        self._current_explanation: str = ""
        self._is_translating: bool = False

        self.lang_map: Dict[str, str] = {
            "中文": "zh-CN",
            "繁体": "zh-TW",
            "English": "en",
            "日本語": "ja",
            "한국어": "ko",
            "Français": "fr",
            "Deutsch": "de",
            "Español": "es",
        }

        self._init_ui()
        self.translation_finished.connect(self._on_translation_success)
        self.translation_failed.connect(self._on_translation_failed)

    def _init_ui(self):
        self.setFixedSize(380, 390)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Main Card Frame
        self.main_card = QFrame(self)
        self.main_card.setObjectName("MainCard")
        self.main_card.setStyleSheet("""
            QFrame#MainCard {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 10px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 3)
        self.main_card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.main_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # --- Top Header ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        # Instant Target Language Dropdown
        self.lang_combo = ComboBox(self)
        self.lang_combo.addItems(list(self.lang_map.keys()))
        self.lang_combo.setFixedWidth(84)
        self.lang_combo.setStyleSheet("font-size: 11px;")
        self.lang_combo.currentIndexChanged.connect(self._on_target_lang_changed)
        header_layout.addWidget(self.lang_combo)

        # Phonetic / Pinyin Label
        self.phonetic_label = QLabel("", self)
        self.phonetic_label.setStyleSheet("""
            color: #605E5C;
            font-size: 11px;
            font-family: Consolas, "Segoe UI", sans-serif;
            background-color: #F3F2F1;
            padding: 2px 6px;
            border-radius: 6px;
        """)
        self.phonetic_label.setVisible(False)
        header_layout.addWidget(self.phonetic_label)
        header_layout.addStretch()

        # Speaker (TTS) Button
        self.tts_btn = QPushButton("🔊", self)
        self.tts_btn.setToolTip("语音朗读")
        self.tts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tts_btn.setFixedSize(30, 26)
        self.tts_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F2F1;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #EDEBE9; }
        """)
        self.tts_btn.clicked.connect(self._on_tts_clicked)
        header_layout.addWidget(self.tts_btn)

        # Ask AI Button
        self.ask_ai_btn = QPushButton("🤖 问 AI", self)
        self.ask_ai_btn.setToolTip("与 AI 展开深度翻译探讨与答疑")
        self.ask_ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask_ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FC;
                color: #0078D4;
                border: 1px solid #C7E0F4;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #DEECF9; }
        """)
        self.ask_ai_btn.clicked.connect(self._on_ask_ai_clicked)
        header_layout.addWidget(self.ask_ai_btn)

        # Copy Button
        self.copy_btn = QPushButton("📋", self)
        self.copy_btn.setToolTip("复制译文")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setFixedSize(30, 26)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F2F1;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #EDEBE9; }
        """)
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        header_layout.addWidget(self.copy_btn)

        # Close Button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8A8886;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #F3F2F1; color: #323130; }
        """)
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.close_btn)

        card_layout.addLayout(header_layout)

        # --- Loading & Error Indicator ---
        self.loading_label = QLabel("⚡ 正在连接 AI 大模型进行深度解析...", self)
        self.loading_label.setStyleSheet("color: #0078D4; font-size: 13px; font-weight: 500; padding: 20px 0;")
        self.loading_label.setWordWrap(True)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.loading_label)

        # --- Scrollable Content Container ---
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 5px; background: transparent; }
            QScrollBar::handle:vertical { background: #C8C6C4; border-radius: 2px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #A19F9D; }
        """)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(10)

        # Section 1: Translation Card
        self.trans_box = QFrame()
        self.trans_box.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E1DFDD;
                border-left: 4px solid #0078D4;
                border-radius: 6px;
                padding: 8px 10px;
            }
        """)
        trans_vbox = QVBoxLayout(self.trans_box)
        trans_vbox.setContentsMargins(4, 2, 4, 2)
        trans_vbox.setSpacing(3)

        lbl_t_title = QLabel("📝 译文", self.trans_box)
        lbl_t_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #605E5C;")
        self.trans_content = QLabel("", self.trans_box)
        self.trans_content.setWordWrap(True)
        self.trans_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.trans_content.setStyleSheet("font-size: 14px; font-weight: 600; color: #201F1E; line-height: 1.4;")
        trans_vbox.addWidget(lbl_t_title)
        trans_vbox.addWidget(self.trans_content)
        self.content_layout.addWidget(self.trans_box)

        # Section 2: Explanation Card
        self.exp_box = QFrame()
        self.exp_box.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #EDEBE9;
                border-radius: 6px;
                padding: 8px 10px;
            }
        """)
        exp_vbox = QVBoxLayout(self.exp_box)
        exp_vbox.setContentsMargins(4, 2, 4, 2)
        exp_vbox.setSpacing(3)

        lbl_e_title = QLabel("💡 解释与语法分析", self.exp_box)
        lbl_e_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #605E5C;")
        self.exp_content = QLabel("", self.exp_box)
        self.exp_content.setWordWrap(True)
        self.exp_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.exp_content.setStyleSheet("font-size: 12px; color: #323130; line-height: 1.4;")
        exp_vbox.addWidget(lbl_e_title)
        exp_vbox.addWidget(self.exp_content)
        self.content_layout.addWidget(self.exp_box)

        # Section 3: Example Sentences Card
        self.ex_box = QFrame()
        self.ex_box.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #EDEBE9;
                border-radius: 6px;
                padding: 8px 10px;
            }
        """)
        ex_vbox = QVBoxLayout(self.ex_box)
        ex_vbox.setContentsMargins(4, 2, 4, 2)
        ex_vbox.setSpacing(4)

        lbl_ex_title = QLabel("📖 实用例句与造句", self.ex_box)
        lbl_ex_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #605E5C;")
        self.ex_content = QLabel("", self.ex_box)
        self.ex_content.setWordWrap(True)
        self.ex_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ex_content.setStyleSheet("font-size: 12px; color: #323130; line-height: 1.4;")
        ex_vbox.addWidget(lbl_ex_title)
        ex_vbox.addWidget(self.ex_content)
        self.content_layout.addWidget(self.ex_box)

        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.setVisible(False)
        card_layout.addWidget(self.scroll_area)

        # --- Bottom Status Bar ---
        footer_layout = QHBoxLayout()
        self.footer_label = QLabel("PMFY • Windows 11 Native", self)
        self.footer_label.setStyleSheet("color: #A19F9D; font-size: 10px;")
        footer_layout.addWidget(self.footer_label)
        footer_layout.addStretch()

        card_layout.addLayout(footer_layout)
        outer_layout.addWidget(self.main_card)

    def show_translation(self, text: str, x: int = 0, y: int = 0):
        self._current_text = text.strip()
        self._current_trans = ""
        self._current_explanation = ""

        # Set dropdown to current configured target language
        cfg_lang = config_manager.get("translation", "target_language", "zh-CN")
        for name, code in self.lang_map.items():
            if code == cfg_lang or (code.startswith("zh") and cfg_lang.startswith("zh")):
                self.lang_combo.blockSignals(True)
                self.lang_combo.setCurrentText(name)
                self.lang_combo.blockSignals(False)
                break

        # Phonetics
        local_phonetic = tts_engine.get_phonetic_or_pinyin(self._current_text)
        if local_phonetic:
            self.phonetic_label.setText(local_phonetic)
            self.phonetic_label.setVisible(True)
        else:
            self.phonetic_label.setVisible(False)

        cursor_pos = QCursor.pos()
        target_x = x if x > 0 else cursor_pos.x()
        target_y = y if y > 0 else cursor_pos.y()

        clamped_x, clamped_y = clamp_rect_to_screen(
            target_x + 10, target_y + 10, self.width(), self.height(), margin=16
        )
        self.move(clamped_x, clamped_y)

        self.loading_label.setText("⚡ 正在连接 AI 大模型进行深度解析...")
        self.loading_label.setStyleSheet("color: #0078D4; font-size: 13px; font-weight: 500; padding: 20px 0;")
        self.loading_label.setVisible(True)
        self.scroll_area.setVisible(False)
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetWindowPos(int(self.winId()), -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
        except Exception:
            pass

        target_lang = self.lang_map.get(self.lang_combo.currentText(), "zh-CN")

        if config_manager.get("translation", "auto_pronounce", False):
            tts_engine.speak(self._current_text)

        self._start_query(target_lang)

    def _start_query(self, target_lang: str):
        if self._is_translating:
            return
        self._is_translating = True

        threading.Thread(
            target=self._fetch_translation,
            args=(self._current_text, target_lang),
            daemon=True
        ).start()

    def _fetch_translation(self, text: str, target_lang: str):
        try:
            result = ai_client.translate_selection(text, target_lang=target_lang)
            if result.get("error"):
                self.translation_failed.emit(result.get("message", "翻译失败"))
            else:
                self.translation_finished.emit(result)
        except Exception as e:
            self.translation_failed.emit(str(e))
        finally:
            self._is_translating = False

    def _on_target_lang_changed(self):
        if self._current_text:
            target_lang = self.lang_map.get(self.lang_combo.currentText(), "zh-CN")
            self.loading_label.setText(f"⚡ 正在重新翻译为【{self.lang_combo.currentText()}】...")
            self.loading_label.setVisible(True)
            self.scroll_area.setVisible(False)
            self._start_query(target_lang)

    def _on_translation_success(self, data: dict):
        self.loading_label.setVisible(False)
        self.scroll_area.setVisible(True)

        self._current_trans = data.get("translation", "")
        self.trans_content.setText(self._current_trans or "（无译文）")

        ai_phonetic = data.get("phonetic", "").strip()
        if ai_phonetic:
            self.phonetic_label.setText(ai_phonetic)
            self.phonetic_label.setVisible(True)

        # Module toggles
        enable_trans = config_manager.get("modules", "enable_translation", True)
        enable_exp = config_manager.get("modules", "enable_explanation", True)
        enable_ex = config_manager.get("modules", "enable_examples", True)

        self.trans_box.setVisible(enable_trans)

        explanation = data.get("explanation", "").strip()
        self._current_explanation = explanation
        if enable_exp and explanation:
            self.exp_box.setVisible(True)
            self.exp_content.setText(explanation)
        else:
            self.exp_box.setVisible(False)

        examples = data.get("examples", [])
        if enable_ex and examples:
            self.ex_box.setVisible(True)
            ex_lines = []
            for i, ex in enumerate(examples, 1):
                src = ex.get("src", "")
                dst = ex.get("dst", "")
                ex_lines.append(f"<b>{i}. {src}</b><br><span style='color: #605E5C;'>{dst}</span>")
            self.ex_content.setText("<br><br>".join(ex_lines))
        else:
            self.ex_box.setVisible(False)

    def _on_translation_failed(self, error_msg: str):
        self.loading_label.setText(f"❌ 翻译失败:\n{error_msg}")
        self.loading_label.setStyleSheet("color: #D13438; font-size: 13px; font-weight: 500; padding: 20px 8px;")
        self.loading_label.setVisible(True)
        self.scroll_area.setVisible(False)

    def _on_ask_ai_clicked(self):
        win = get_ask_ai_window()
        win.set_context(
            original_text=self._current_text,
            translated_text=self._current_trans,
            extra_context=self._current_explanation
        )
        win.show_on_top()

    def _on_tts_clicked(self):
        if self._current_text:
            tts_engine.speak(self._current_text)

    def _on_copy_clicked(self):
        if self._current_trans:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._current_trans)
            self.copy_btn.setText("✓")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋"))
