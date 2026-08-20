import threading
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    ComboBox,
    FluentIcon as FIF,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TextEdit,
    TitleLabel,
    TransparentPushButton,
)

from app.config import config_manager
from app.core.ai_client import ai_client
from app.core.tts_engine import tts_engine
from app.ui.ask_ai_window import get_ask_ai_window
from app.ui.theme import ACCENT_COLOR


class InputTranslationWindow(QWidget):
    """Windows 11 Fluent Interactive Studio for Direct Text Input Translation."""

    translation_ready = pyqtSignal(dict, str)  # (result_data, query_text)
    translation_failed = pyqtSignal(str, str)  # (error_msg, query_text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PMFY - 双语输入翻译工作台")
        self.setMinimumSize(640, 540)
        self.resize(720, 600)

        self._last_query_text: str = ""
        self._current_trans: str = ""
        self._current_exp: str = ""

        # 500ms Debounce Timer for real-time translation as user types
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(500)
        self._debounce_timer.timeout.connect(self._execute_translation)

        self.lang_map: Dict[str, str] = {
            "简体中文": "zh-CN",
            "English": "en",
            "繁體中文": "zh-TW",
            "日本語": "ja",
            "한국어": "ko",
            "Français": "fr",
            "Deutsch": "de",
            "Español": "es",
            "Русский": "ru",
        }

        self._init_ui()

        self.translation_ready.connect(self._on_translation_ready)
        self.translation_failed.connect(self._on_translation_failed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # 1. Top Language Selection Bar
        lang_bar = QHBoxLayout()
        lang_bar.setSpacing(8)

        icon = IconWidget(FIF.LANGUAGE, self)
        icon.setFixedSize(22, 22)
        lang_bar.addWidget(icon)

        self.src_combo = ComboBox(self)
        self.src_combo.addItems(["自动检测 (Auto)"] + list(self.lang_map.keys()))
        self.src_combo.setFixedWidth(130)
        lang_bar.addWidget(self.src_combo)

        btn_swap = PushButton("⇄", self)
        btn_swap.setFixedWidth(40)
        btn_swap.setToolTip("互换语言")
        btn_swap.clicked.connect(self._on_swap_languages)
        lang_bar.addWidget(btn_swap)

        self.dst_combo = ComboBox(self)
        self.dst_combo.addItems(list(self.lang_map.keys()))
        self.dst_combo.setCurrentText("简体中文")
        self.dst_combo.setFixedWidth(130)
        self.dst_combo.currentIndexChanged.connect(self._trigger_debounce)
        lang_bar.addWidget(self.dst_combo)

        lang_bar.addStretch()

        btn_paste = PushButton("📋 粘贴", self)
        btn_paste.clicked.connect(self._on_paste_clicked)
        lang_bar.addWidget(btn_paste)

        btn_clear = PushButton("🗑️ 清空", self)
        btn_clear.clicked.connect(self._on_clear_clicked)
        lang_bar.addWidget(btn_clear)

        main_layout.addLayout(lang_bar)

        # 2. Source Input Area
        self.input_card = CardWidget(self)
        input_layout = QVBoxLayout(self.input_card)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(6)

        self.input_edit = TextEdit(self.input_card)
        self.input_edit.setPlaceholderText("在此键入或粘贴需要翻译的文本（支持自动实时防抖翻译）...")
        self.input_edit.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.input_edit)

        input_footer = QHBoxLayout()
        self.char_count_lbl = QLabel("0 字符", self.input_card)
        self.char_count_lbl.setStyleSheet("color: #8A8886; font-size: 11px;")
        input_footer.addWidget(self.char_count_lbl)
        input_footer.addStretch()
        input_layout.addLayout(input_footer)

        main_layout.addWidget(self.input_card, stretch=2)

        # 3. Translation Result Area
        self.result_card = CardWidget(self)
        res_layout = QVBoxLayout(self.result_card)
        res_layout.setContentsMargins(14, 12, 14, 12)
        res_layout.setSpacing(8)

        res_header = QHBoxLayout()
        self.res_title = QLabel("📝 翻译结果", self.result_card)
        self.res_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #201F1E;")
        res_header.addWidget(self.res_title)

        self.phonetic_lbl = QLabel("", self.result_card)
        self.phonetic_lbl.setStyleSheet("color: #605E5C; font-size: 11px; background: #F3F2F1; padding: 2px 6px; border-radius: 4px;")
        self.phonetic_lbl.hide()
        res_header.addWidget(self.phonetic_lbl)
        res_header.addStretch()

        self.btn_tts = PushButton("🔊 发音", self.result_card)
        self.btn_tts.clicked.connect(self._on_tts_clicked)
        res_header.addWidget(self.btn_tts)

        self.btn_ask_ai = PushButton("🤖 问 AI", self.result_card)
        self.btn_ask_ai.setStyleSheet("color: #0078D4; font-weight: bold;")
        self.btn_ask_ai.clicked.connect(self._on_ask_ai_clicked)
        res_header.addWidget(self.btn_ask_ai)

        self.btn_copy_res = PushButton("📋 复制", self.result_card)
        self.btn_copy_res.clicked.connect(self._on_copy_result)
        res_header.addWidget(self.btn_copy_res)

        res_layout.addLayout(res_header)

        # Scroll area for multi-part results
        self.scroll_res = QScrollArea(self.result_card)
        self.scroll_res.setWidgetResizable(True)
        self.scroll_res.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.res_content_widget = QWidget()
        self.res_content_layout = QVBoxLayout(self.res_content_widget)
        self.res_content_layout.setContentsMargins(0, 0, 4, 0)
        self.res_content_layout.setSpacing(8)

        self.trans_text_lbl = QLabel("（等待输入...）", self.res_content_widget)
        self.trans_text_lbl.setWordWrap(True)
        self.trans_text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.trans_text_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #201F1E; line-height: 1.5;")
        self.res_content_layout.addWidget(self.trans_text_lbl)

        self.exp_box = QFrame()
        self.exp_box.setStyleSheet("background: #F9F9FB; border-radius: 6px; padding: 6px 10px;")
        exp_vbox = QVBoxLayout(self.exp_box)
        exp_vbox.setContentsMargins(4, 4, 4, 4)
        lbl_e = QLabel("💡 详细释义与语法分析", self.exp_box)
        lbl_e.setStyleSheet("font-size: 11px; font-weight: bold; color: #605E5C;")
        self.exp_lbl = QLabel("", self.exp_box)
        self.exp_lbl.setWordWrap(True)
        self.exp_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.exp_lbl.setStyleSheet("font-size: 12px; color: #323130;")
        exp_vbox.addWidget(lbl_e)
        exp_vbox.addWidget(self.exp_lbl)
        self.exp_box.hide()
        self.res_content_layout.addWidget(self.exp_box)

        self.ex_box = QFrame()
        self.ex_box.setStyleSheet("background: #F9F9FB; border-radius: 6px; padding: 6px 10px;")
        ex_vbox = QVBoxLayout(self.ex_box)
        ex_vbox.setContentsMargins(4, 4, 4, 4)
        lbl_ex = QLabel("📖 实用例句与造句", self.ex_box)
        lbl_ex.setStyleSheet("font-size: 11px; font-weight: bold; color: #605E5C;")
        self.ex_lbl = QLabel("", self.ex_box)
        self.ex_lbl.setWordWrap(True)
        self.ex_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ex_lbl.setStyleSheet("font-size: 12px; color: #323130;")
        ex_vbox.addWidget(lbl_ex)
        ex_vbox.addWidget(self.ex_lbl)
        self.ex_box.hide()
        self.res_content_layout.addWidget(self.ex_box)

        self.scroll_res.setWidget(self.res_content_widget)
        res_layout.addWidget(self.scroll_res, stretch=1)

        main_layout.addWidget(self.result_card, stretch=3)

    def show_window(self, initial_text: str = ""):
        if initial_text:
            self.input_edit.setText(initial_text)
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_text_changed(self):
        text = self.input_edit.toPlainText()
        self.char_count_lbl.setText(f"{len(text)} 字符")
        self._trigger_debounce()

    def _trigger_debounce(self):
        self._debounce_timer.stop()
        self._debounce_timer.start()

    def _execute_translation(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            self.trans_text_lbl.setText("（等待输入...）")
            self.exp_box.hide()
            self.ex_box.hide()
            self.phonetic_lbl.hide()
            return

        self._last_query_text = text
        self.trans_text_lbl.setText("⚡ 正在翻译中...")

        dst_code = self.lang_map.get(self.dst_combo.currentText(), "zh-CN")

        def _worker(q_text: str, t_lang: str):
            try:
                res = ai_client.translate_selection(q_text, target_lang=t_lang)
                if res.get("error"):
                    self.translation_failed.emit(res.get("message", "翻译失败"), q_text)
                else:
                    self.translation_ready.emit(res, q_text)
            except Exception as e:
                self.translation_failed.emit(str(e), q_text)

        threading.Thread(target=_worker, args=(text, dst_code), daemon=True).start()

    def _on_translation_ready(self, data: dict, query_text: str):
        # Ignore out-of-date responses if user continued typing
        if query_text != self._last_query_text:
            return

        self._current_trans = data.get("translation", "")
        self.trans_text_lbl.setText(self._current_trans or "（无译文）")

        phonetic = data.get("phonetic", "").strip() or tts_engine.get_phonetic_or_pinyin(query_text)
        if phonetic:
            self.phonetic_lbl.setText(phonetic)
            self.phonetic_lbl.show()
        else:
            self.phonetic_lbl.hide()

        explanation = data.get("explanation", "").strip()
        self._current_exp = explanation
        if explanation:
            self.exp_lbl.setText(explanation)
            self.exp_box.show()
        else:
            self.exp_box.hide()

        examples = data.get("examples", [])
        if examples:
            ex_lines = []
            for i, ex in enumerate(examples, 1):
                src = ex.get("src", "")
                dst = ex.get("dst", "")
                ex_lines.append(f"<b>{i}. {src}</b><br><span style='color: #605E5C;'>{dst}</span>")
            self.ex_lbl.setText("<br><br>".join(ex_lines))
            self.ex_box.show()
        else:
            self.ex_box.hide()

    def _on_translation_failed(self, error_msg: str, query_text: str):
        if query_text != self._last_query_text:
            return
        self.trans_text_lbl.setText(f"❌ 翻译失败: {error_msg}")
        self.exp_box.hide()
        self.ex_box.hide()

    def _on_swap_languages(self):
        src = self.src_combo.currentText()
        dst = self.dst_combo.currentText()
        if src in self.lang_map and dst in self.lang_map:
            self.src_combo.setCurrentText(dst)
            self.dst_combo.setCurrentText(src)

    def _on_clear_clicked(self):
        self.input_edit.clear()
        self.trans_text_lbl.setText("（等待输入...）")
        self.exp_box.hide()
        self.ex_box.hide()
        self.phonetic_lbl.hide()

    def _on_paste_clicked(self):
        cb_text = QApplication.clipboard().text()
        if cb_text:
            self.input_edit.setText(cb_text)

    def _on_copy_result(self):
        if self._current_trans:
            QApplication.clipboard().setText(self._current_trans)
            self.btn_copy_res.setText("✓ 已复制")
            QTimer.singleShot(1500, lambda: self.btn_copy_res.setText("📋 复制"))

    def _on_tts_clicked(self):
        text = self.input_edit.toPlainText().strip()
        if text:
            tts_engine.speak(text)

    def _on_ask_ai_clicked(self):
        text = self.input_edit.toPlainText().strip()
        win = get_ask_ai_window()
        win.set_context(
            original_text=text,
            translated_text=self._current_trans,
            extra_context=self._current_exp
        )
        win.show_on_top()
