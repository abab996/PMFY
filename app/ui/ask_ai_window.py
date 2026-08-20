import threading
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    FluentIcon as FIF,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PasswordLineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TextEdit,
    Theme,
    TitleLabel,
    TransparentPushButton,
    setTheme,
    setThemeColor,
)

from app.core.ai_client import ai_client
from app.ui.theme import ACCENT_COLOR


class MessageBubble(QFrame):
    """Chat message bubble for user and AI with full Markdown & code block rendering."""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.is_user = is_user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(0)

        if is_user:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {ACCENT_COLOR};
                    border-radius: 12px;
                    border-bottom-right-radius: 2px;
                }}
            """)
            css = """
                body {
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    font-size: 13px;
                    line-height: 1.45;
                    color: #FFFFFF;
                }
                p { margin: 2px 0; }
                code {
                    font-family: 'Consolas', 'Courier New', monospace;
                    background-color: rgba(255, 255, 255, 0.22);
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-size: 12px;
                    color: #FFFFFF;
                }
                pre {
                    font-family: 'Consolas', 'Courier New', monospace;
                    background-color: rgba(0, 0, 0, 0.18);
                    padding: 6px 8px;
                    border-radius: 6px;
                    margin: 4px 0;
                    color: #FFFFFF;
                }
                a { color: #E0F2FE; text-decoration: underline; }
            """
        else:
            self.setStyleSheet("""
                QFrame {{
                    background-color: #FFFFFF;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 12px;
                    border-bottom-left-radius: 2px;
                }}
            """)
            css = """
                body {
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    font-size: 13px;
                    line-height: 1.5;
                    color: #201F1E;
                }
                h1, h2, h3, h4, h5, h6 {
                    margin: 6px 0 3px 0;
                    font-weight: bold;
                    color: #111827;
                }
                h1 { font-size: 16px; }
                h2 { font-size: 15px; }
                h3 { font-size: 14px; }
                h4 { font-size: 13px; }
                p { margin: 3px 0; }
                ul, ol { margin: 3px 0; padding-left: 18px; }
                li { margin: 2px 0; }
                code {
                    font-family: 'Consolas', 'Courier New', monospace;
                    background-color: #F3F4F6;
                    color: #D946EF;
                    padding: 1px 4px;
                    border-radius: 4px;
                    font-size: 12px;
                    border: 1px solid #E5E7EB;
                }
                pre {
                    font-family: 'Consolas', 'Courier New', monospace;
                    background-color: #F8FAFC;
                    padding: 8px 10px;
                    border-radius: 6px;
                    border: 1px solid #E2E8F0;
                    margin: 6px 0;
                    color: #0F172A;
                }
                blockquote {
                    border-left: 3px solid #0078D4;
                    margin: 4px 0;
                    padding-left: 8px;
                    color: #64748B;
                    background-color: #F8FAFC;
                }
                table {
                    border-collapse: collapse;
                    margin: 6px 0;
                    width: 100%;
                }
                th, td {
                    border: 1px solid #E2E8F0;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                th {
                    background-color: #F1F5F9;
                    font-weight: bold;
                }
                a { color: #0078D4; text-decoration: none; }
                hr { border: none; border-top: 1px solid #E2E8F0; margin: 6px 0; }
            """

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.browser.setFrameShape(QFrame.Shape.NoFrame)
        self.browser.setStyleSheet("background: transparent; border: none;")
        self.browser.document().setDocumentMargin(0)
        self.browser.document().setDefaultStyleSheet(css)
        self.browser.setMarkdown(text)

        self.setMaximumWidth(440)
        layout.addWidget(self.browser)
        self._update_height()

    def _update_height(self):
        doc_w = self.width() - 24 if self.width() > 24 else 380
        self.browser.document().setTextWidth(doc_w)
        h = int(self.browser.document().size().height())
        self.browser.setFixedHeight(max(22, h + 6))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_height()


class AskAIWindow(QWidget):
    """Windows 11 Fluent Chat Dialog with AI for Deep Translation Discussions."""

    ai_responded = pyqtSignal(str)
    ai_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PMFY - 问 AI 智能讨论")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(480, 500)
        self.resize(500, 580)

        self._context_str: str = ""
        self._history: List[Dict[str, str]] = []
        self._is_waiting: bool = False

        self._init_ui()

        self.ai_responded.connect(self._on_ai_responded)
        self.ai_failed.connect(self._on_ai_failed)

    def show_on_top(self):
        """Displays AskAIWindow and forces it to the front even over fullscreen topmost windows."""
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # HWND_TOPMOST = -1, SWP_NOMOVE = 0x2, SWP_NOSIZE = 0x1, SWP_SHOWWINDOW = 0x40
            user32.SetWindowPos(int(self.winId()), -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            user32.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Top Header Bar
        header = QHBoxLayout()
        icon = IconWidget(FIF.CHAT, self)
        icon.setFixedSize(24, 24)
        title = TitleLabel("问 AI 智能讨论", self)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()

        self.btn_clear = TransparentPushButton("清空历史", self, FIF.DELETE)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        header.addWidget(self.btn_clear)

        main_layout.addLayout(header)

        # 2. Context Card (Collapsible Reference Area)
        self.context_card = CardWidget(self)
        ctx_layout = QVBoxLayout(self.context_card)
        ctx_layout.setContentsMargins(14, 10, 14, 10)
        ctx_layout.setSpacing(4)

        ctx_title = QLabel("📌 当前参考语境与原文：", self.context_card)
        ctx_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {ACCENT_COLOR};")
        self.ctx_label = QLabel("", self.context_card)
        self.ctx_label.setStyleSheet("font-size: 12px; color: #605E5C;")
        self.ctx_label.setWordWrap(True)
        self.ctx_label.setMaximumHeight(80)
        ctx_layout.addWidget(ctx_title)
        ctx_layout.addWidget(self.ctx_label)
        main_layout.addWidget(self.context_card)

        # 3. Quick Prompt Preset Action Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        chips = [
            ("🔍 语法与结构解析", "请帮我详细剖析这段文字的语法结构、修辞手法与长难句难点。"),
            ("🗣️ 地道口语表达", "请为这段文字提供 2-3 种更地道、口语化的表达方式，并说明使用语境。"),
            ("💼 商务专业改写", "请将这段文字改写为更地道、专业的商务正式文风。"),
            ("❓ 词义辨析", "请帮我分析这里的重点单词/短语有哪些常见同义词，以及它们之间的细微差别。"),
        ]

        for chip_text, chip_prompt in chips:
            btn_chip = PushButton(chip_text, self)
            btn_chip.setStyleSheet("""
                QPushButton {
                    background-color: #F3F2F1;
                    color: #323130;
                    border: 1px solid rgba(0,0,0,0.06);
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #EFF6FC;
                    color: #0078D4;
                    border-color: #C7E0F4;
                }
            """)
            btn_chip.clicked.connect(lambda checked, p=chip_prompt: self.send_user_message(p))
            chips_layout.addWidget(btn_chip)

        chips_layout.addStretch()
        main_layout.addLayout(chips_layout)

        # 4. Message Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: #F9F9FB; border-radius: 10px; }
            QScrollBar:vertical { width: 5px; background: transparent; }
            QScrollBar::handle:vertical { background: #C8C6C4; border-radius: 2px; }
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(14, 14, 14, 14)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()
        self.scroll_area.setWidget(self.messages_container)

        main_layout.addWidget(self.scroll_area, stretch=1)

        # 5. Input Bar
        input_box = QHBoxLayout()
        input_box.setSpacing(8)

        self.input_edit = LineEdit(self)
        self.input_edit.setPlaceholderText("向 AI 提问任何关于该翻译、词汇用法或语法的疑问 (Enter 发送)...")
        self.input_edit.returnPressed.connect(self._on_send_clicked)
        input_box.addWidget(self.input_edit, stretch=1)

        self.btn_send = PrimaryPushButton("发送", self, FIF.SEND)
        self.btn_send.setFixedWidth(90)
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_box.addWidget(self.btn_send)

        main_layout.addLayout(input_box)

    def set_context(self, original_text: str, translated_text: str = "", extra_context: str = ""):
        """Sets the conversation background context."""
        parts = []
        if original_text:
            parts.append(f"【原文】：{original_text}")
        if translated_text:
            parts.append(f"【当前译文】：{translated_text}")
        if extra_context:
            parts.append(f"【屏幕背景】：{extra_context[:300]}")

        self._context_str = "\n".join(parts)
        self.ctx_label.setText(self._context_str or "（无特殊上下文）")
        self.clear_conversation(show_welcome=True)

    def _on_clear_clicked(self):
        self.clear_conversation(show_welcome=True)
        InfoBar.success(
            title="已清空",
            content="对话历史已成功清空",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def clear_conversation(self, show_welcome: bool = False):
        """Cleans up all messages, deletes orphaned child widgets, and prevents stacking."""
        self._history.clear()

        # 1. Directly remove and delete all MessageBubble instances inside container
        for bubble in self.messages_container.findChildren(MessageBubble):
            bubble.setParent(None)
            bubble.deleteLater()

        # 2. Clear out all layout items and sub-layouts
        while self.messages_layout.count() > 0:
            item = self.messages_layout.takeAt(0)
            sub_layout = item.layout()
            if sub_layout is not None:
                while sub_layout.count() > 0:
                    sub_item = sub_layout.takeAt(0)
                    w = sub_item.widget()
                    if w is not None:
                        w.setParent(None)
                        w.deleteLater()
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        # 3. Restore bottom stretch spacer
        self.messages_layout.addStretch()

        # 4. Re-add welcome message if requested
        if show_welcome:
            welcome_text = "您好！我是您的 AI 翻译助手。我已经加载了您当前选中的文字与翻译背景，您可以点击上方快捷气泡或在下方输入任何疑问。"
            self._append_message(welcome_text, is_user=False)

    def send_user_message(self, text: str):
        text = text.strip()
        if not text or self._is_waiting:
            return

        self._is_waiting = True
        self.btn_send.setEnabled(False)
        self.btn_send.setText("思考中...")
        self.input_edit.clear()

        # Append to UI
        self._append_message(text, is_user=True)
        self._history.append({"role": "user", "content": text})

        # Run in worker thread
        threading.Thread(
            target=self._worker_chat,
            args=(list(self._history), self._context_str),
            daemon=True
        ).start()

    def _worker_chat(self, history: list, context: str):
        try:
            resp_text = ai_client.chat_with_ai(history, context=context)
            self.ai_responded.emit(resp_text)
        except Exception as e:
            self.ai_failed.emit(str(e))

    def _on_ai_responded(self, text: str):
        self._is_waiting = False
        self.btn_send.setEnabled(True)
        self.btn_send.setText("发送")

        self._append_message(text, is_user=False)
        self._history.append({"role": "assistant", "content": text})
        self._scroll_to_bottom()

    def _on_ai_failed(self, err: str):
        self._is_waiting = False
        self.btn_send.setEnabled(True)
        self.btn_send.setText("发送")
        self._append_message(f"❌ 提问失败: {err}", is_user=False)
        self._scroll_to_bottom()

    def _on_send_clicked(self):
        text = self.input_edit.text()
        self.send_user_message(text)

    def _append_message(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user=is_user, parent=self.messages_container)
        
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        if is_user:
            row_layout.addStretch()
            row_layout.addWidget(bubble, stretch=0)
        else:
            row_layout.addWidget(bubble, stretch=0)
            row_layout.addStretch()

        # Insert before bottom stretch
        idx = max(0, self.messages_layout.count() - 1)
        self.messages_layout.insertLayout(idx, row_layout)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))


ask_ai_window: Optional[AskAIWindow] = None


def get_ask_ai_window() -> AskAIWindow:
    global ask_ai_window
    if ask_ai_window is None:
        ask_ai_window = AskAIWindow()
    return ask_ai_window
