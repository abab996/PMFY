import io
import os
import threading
import time
from typing import Any, Dict, List, Optional

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CardWidget, PrimaryPushButton, ProgressBar, PushButton

from app.config import config_manager
from app.core.ai_client import ai_client
from app.core.ocr_engine import ocr_engine
from app.core.screen_capture import screen_capture
from app.ui.ask_ai_window import get_ask_ai_window
from app.ui.theme import ACCENT_COLOR
from app.utils.screen_utils import clamp_rect_to_screen


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    qimg = QImage()
    qimg.loadFromData(img_byte_arr.getvalue())
    return QPixmap.fromImage(qimg)


class ConfirmCard(QFrame):
    """Floating confirmation card for right-click area snipping."""

    confirmed = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0, 0, 0, 0.16);
                border-radius: 10px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        lbl = QLabel("✨ 确认翻译此选区？", self)
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #201F1E;")
        layout.addWidget(lbl)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_confirm = PrimaryPushButton("✓ 确认翻译", self)
        self.btn_confirm.setFixedHeight(28)
        self.btn_confirm.clicked.connect(self.confirmed.emit)
        btn_box.addWidget(self.btn_confirm)

        self.btn_cancel = PushButton("✕ 取消", self)
        self.btn_cancel.setFixedHeight(28)
        self.btn_cancel.clicked.connect(self.cancelled.emit)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        self.adjustSize()
        self.hide()


class AreaSelectionTooltipBar(QFrame):
    """Floating mini action toolbar for selecting text in the area viewer."""

    copy_clicked = pyqtSignal(str)
    translate_clicked = pyqtSignal(str, int, int)
    ask_ai_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text: str = ""
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0, 0, 0, 0.16);
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                color: #201F1E;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.08); }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self.btn_copy = QPushButton("📋 复制", self)
        self.btn_copy.clicked.connect(self._on_copy_click)
        layout.addWidget(self.btn_copy)

        self.btn_trans = QPushButton("🔍 详细翻译", self)
        self.btn_trans.clicked.connect(self._on_trans_click)
        layout.addWidget(self.btn_trans)

        self.btn_ask = QPushButton("🤖 问AI", self)
        self.btn_ask.setStyleSheet("color: #0078D4; font-weight: bold;")
        self.btn_ask.clicked.connect(self._on_ask_click)
        layout.addWidget(self.btn_ask)

        btn_close = QPushButton("✕", self)
        btn_close.setFixedWidth(20)
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

        self.adjustSize()
        self.hide()

    def show_for_text(self, text: str, pos: QPoint):
        self._text = text.strip()
        self.btn_copy.setText("📋 复制")
        self.move(pos)
        self.show()
        self.raise_()

    def _on_copy_click(self):
        if self._text:
            QApplication.clipboard().setText(self._text)
            self.btn_copy.setText("✓ 已复制")
            self.copy_clicked.emit(self._text)
            QTimer.singleShot(1200, self.hide)

    def _on_trans_click(self):
        if self._text:
            cursor_pos = QCursor.pos()
            self.translate_clicked.emit(self._text, cursor_pos.x(), cursor_pos.y())
            self.hide()

    def _on_ask_click(self):
        if self._text:
            self.ask_ai_clicked.emit(self._text)
            self.hide()


class AreaTranslationViewer(QWidget):
    """Interactive floating window for cropped area translation with text selection & toolbars."""

    detail_translate_requested = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PMFY - 选区原位翻译")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._original_pil: Optional[Image.Image] = None
        self._translated_pil: Optional[Image.Image] = None
        self._original_pix: Optional[QPixmap] = None
        self._translated_pix: Optional[QPixmap] = None
        self._ocr_blocks: List[Dict[str, Any]] = []
        self._translated_texts: List[str] = []
        self._show_original = False

        # Selection state inside area viewer
        self._is_selecting = False
        self._selection_start = QPoint()
        self._selection_end = QPoint()
        self._img_rect = QRect()

        self._init_ui()

    def _init_ui(self):
        self.setMinimumSize(460, 340)
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(12, 10, 12, 10)
        self.layout_main.setSpacing(8)

        # 1. Top Action Toolbar
        self.toolbar_widget = QWidget(self)
        self.toolbar = QHBoxLayout(self.toolbar_widget)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.setSpacing(6)

        self.badge = QLabel("✂️ 选区翻译", self.toolbar_widget)
        self.badge.setStyleSheet(f"color: {ACCENT_COLOR}; font-weight: bold; font-size: 13px;")
        self.toolbar.addWidget(self.badge)
        self.toolbar.addStretch()

        self.btn_compare = PushButton("👁️ 对比原图", self.toolbar_widget)
        self.btn_compare.pressed.connect(self._on_compare_press)
        self.btn_compare.released.connect(self._on_compare_release)
        self.toolbar.addWidget(self.btn_compare)

        self.btn_ask = PushButton("🤖 问 AI", self.toolbar_widget)
        self.btn_ask.clicked.connect(self._on_ask_clicked)
        self.toolbar.addWidget(self.btn_ask)

        self.btn_copy = PushButton("📋 复制全部", self.toolbar_widget)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        self.toolbar.addWidget(self.btn_copy)

        self.btn_save = PushButton("💾 保存", self.toolbar_widget)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.toolbar.addWidget(self.btn_save)

        self.layout_main.addWidget(self.toolbar_widget)
        self.layout_main.addStretch(1)

        # 2. Dynamic Win11 Acrylic Pill Progress HUD
        self.hud_card = QFrame(self)
        self.hud_card.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 28, 0.94);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 14px;
            }
        """)
        hud_shadow = QGraphicsDropShadowEffect(self.hud_card)
        hud_shadow.setBlurRadius(24)
        hud_shadow.setColor(QColor(0, 0, 0, 90))
        hud_shadow.setOffset(0, 2)
        self.hud_card.setGraphicsEffect(hud_shadow)

        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(20, 12, 20, 12)
        hud_layout.setSpacing(8)

        self.hud_label = QLabel("🚀 正在调用 OCR 识别选区文字...", self.hud_card)
        self.hud_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
        self.hud_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hud_layout.addWidget(self.hud_label)

        self.hud_progress = ProgressBar(self.hud_card)
        self.hud_progress.setValue(15)
        self.hud_progress.setFixedHeight(5)
        hud_layout.addWidget(self.hud_progress)

        self.hud_card.setFixedSize(360, 68)
        self.hud_card.hide()

        # 3. Floating Mini Tooltip Bar for selecting text in translated crop
        self.selection_bar = AreaSelectionTooltipBar(self)
        self.selection_bar.translate_clicked.connect(self._on_bar_translate)
        self.selection_bar.ask_ai_clicked.connect(self._on_bar_ask_ai)

    def show_initial_crop(self, crop_pil: Image.Image, target_rect: QRect):
        """Displays viewer immediately with initial cropped area and progress HUD."""
        self._original_pil = crop_pil
        self._translated_pil = None
        self._original_pix = pil_to_qpixmap(crop_pil)
        self._translated_pix = None
        self._ocr_blocks = []
        self._translated_texts = []
        self._show_original = False
        self.selection_bar.hide()

        self.badge.setText("✂️ 正在翻译选区...")
        self.btn_compare.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self.btn_ask.setEnabled(False)
        self.btn_save.setEnabled(False)

        self._show_window_at_target(target_rect, crop_pil.width, crop_pil.height)
        self.update_progress("🚀 正在调用 OCR 识别选区文字...", 15)
        self.update()

    def update_progress(self, message: str, percent: int):
        """Updates the capsule progress HUD."""
        self.hud_label.setText(message)
        self.hud_progress.setValue(max(0, min(100, percent)))
        self.hud_card.show()
        self.hud_card.raise_()
        self._reposition_hud()

    def display_result(
        self,
        orig_pil: Image.Image,
        trans_pil: Image.Image,
        blocks: List[Dict[str, Any]],
        texts: List[str],
        target_rect: QRect,
    ):
        """Displays finalized in-place translated crop result and enables text selection."""
        self.hud_card.hide()
        self._original_pil = orig_pil
        self._translated_pil = trans_pil
        self._original_pix = pil_to_qpixmap(orig_pil)
        self._translated_pix = pil_to_qpixmap(trans_pil)
        self._ocr_blocks = blocks
        self._translated_texts = texts
        self._show_original = False
        self.selection_bar.hide()

        count_text = f" (共 {len(texts)} 处文本)" if texts else " (未检测到文字)"
        self.badge.setText(f"✅ 选区翻译完成{count_text}")
        self.btn_compare.setEnabled(True)
        self.btn_copy.setEnabled(True)
        self.btn_ask.setEnabled(True)
        self.btn_save.setEnabled(True)

        self._show_window_at_target(target_rect, orig_pil.width, orig_pil.height)
        self.update()

    def _reposition_hud(self):
        cw = self.width()
        ch = self.height()
        hw = self.hud_card.width()
        hh = self.hud_card.height()
        hx = max(10, (cw - hw) // 2)
        hy = max(10, int(ch * 0.65) - hh // 2)
        self.hud_card.move(hx, hy)

    def _show_window_at_target(self, target_rect: QRect, orig_w: int, orig_h: int):
        win_w = max(480, min(980, orig_w + 40))
        win_h = max(360, min(760, orig_h + 90))
        self.resize(win_w, win_h)

        clamped_x, clamped_y = clamp_rect_to_screen(
            target_rect.x(), target_rect.y(), win_w, win_h, margin=15
        )
        self.move(clamped_x, clamped_y)

        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetWindowPos(int(self.winId()), -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            user32.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def _on_bar_translate(self, text: str, pos_x: int, pos_y: int):
        self.selection_bar.hide()
        self.detail_translate_requested.emit(text, pos_x, pos_y)

    def _on_bar_ask_ai(self, text: str):
        self.selection_bar.hide()
        win = get_ask_ai_window()
        win.set_context(original_text=text, extra_context="\n".join(self._translated_texts))
        win.show_on_top()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            self._selection_start = event.pos()
            self._selection_end = event.pos()
            self.selection_bar.hide()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            self._selection_end = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._handle_selection_finished()
            self.update()
        super().mouseReleaseEvent(event)

    def _handle_selection_finished(self):
        rx = min(self._selection_start.x(), self._selection_end.x())
        ry = min(self._selection_start.y(), self._selection_end.y())
        rw = abs(self._selection_end.x() - self._selection_start.x())
        rh = abs(self._selection_end.y() - self._selection_start.y())

        if rw < 8 or rh < 8 or self._original_pil is None or self._img_rect.isEmpty():
            self.selection_bar.hide()
            return

        img_w = self._original_pil.width
        img_h = self._original_pil.height
        tx, ty, tw, th = self._img_rect.x(), self._img_rect.y(), self._img_rect.width(), self._img_rect.height()

        # Map selection rect from viewport back to crop PIL coordinates
        img_x0 = max(0, int(((rx - tx) / max(1, tw)) * img_w))
        img_y0 = max(0, int(((ry - ty) / max(1, th)) * img_h))
        img_x1 = min(img_w, int(((rx + rw - tx) / max(1, tw)) * img_w))
        img_y1 = min(img_h, int(((ry + rh - ty) / max(1, th)) * img_h))

        if img_x1 <= img_x0 or img_y1 <= img_y0:
            self.selection_bar.hide()
            return

        # 1. Match intersecting blocks
        matching_blocks = []
        for i, b in enumerate(self._ocr_blocks):
            bx, by, bw, bh = b["rect"]
            bx1, by1 = bx + bw, by + bh
            inter_x = max(0, min(img_x1, bx1) - max(img_x0, bx))
            inter_y = max(0, min(img_y1, by1) - max(img_y0, by))
            if inter_x > 0 and inter_y > 0:
                t = self._translated_texts[i] if (i < len(self._translated_texts) and self._translated_texts[i]) else b.get("text", "")
                if t.strip():
                    matching_blocks.append((by, bx, t.strip()))

        matching_blocks.sort(key=lambda item: (item[0], item[1]))
        found_texts = [item[2] for item in matching_blocks]

        # 2. Local fallback OCR crop if no blocks matched
        if not found_texts and (img_x1 - img_x0 > 15) and (img_y1 - img_y0 > 15):
            try:
                sub_crop = self._original_pil.crop((img_x0, img_y0, img_x1, img_y1))
                sub_blocks = ocr_engine.recognize(sub_crop)
                found_texts = [b["text"].strip() for b in sub_blocks if b.get("text")]
            except Exception:
                pass

        if found_texts:
            selected_text = " ".join(found_texts)
            bar_x = min(self.width() - 240, max(10, rx))
            bar_y = max(45, ry - 38)
            if bar_y < 50:
                bar_y = min(self.height() - 45, ry + rh + 8)
            self.selection_bar.show_for_text(selected_text, QPoint(bar_x, bar_y))
        else:
            self.selection_bar.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Background fill
        painter.fillRect(self.rect(), QColor(24, 24, 27))

        # Calculate Image Render Rect
        content_rect = QRect(12, 48, self.width() - 24, self.height() - 58)
        pix = self._original_pix if self._show_original else (self._translated_pix or self._original_pix)

        if pix and not pix.isNull():
            img_w = pix.width()
            img_h = pix.height()
            img_aspect = img_w / max(1, img_h)
            content_aspect = content_rect.width() / max(1, content_rect.height())

            if content_aspect > img_aspect:
                target_h = content_rect.height()
                target_w = int(target_h * img_aspect)
            else:
                target_w = content_rect.width()
                target_h = int(target_w / img_aspect)

            target_x = content_rect.x() + (content_rect.width() - target_w) // 2
            target_y = content_rect.y() + (content_rect.height() - target_h) // 2
            self._img_rect = QRect(target_x, target_y, target_w, target_h)

            painter.drawPixmap(self._img_rect, pix)

            # Border around image
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
            painter.drawRect(self._img_rect)

        # Draw left mouse selection box
        if self._is_selecting:
            rx = min(self._selection_start.x(), self._selection_end.x())
            ry = min(self._selection_start.y(), self._selection_end.y())
            rw = abs(self._selection_end.x() - self._selection_start.x())
            rh = abs(self._selection_end.y() - self._selection_start.y())
            sel_rect = QRect(rx, ry, rw, rh)

            # Translucent blue highlight
            painter.fillRect(sel_rect, QColor(0, 120, 212, 50))
            painter.setPen(QPen(QColor(0, 120, 212, 220), 1.5, Qt.PenStyle.SolidLine))
            painter.drawRect(sel_rect)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_hud()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(30, self._reposition_hud)

    def _on_compare_press(self):
        self._show_original = True
        self.update()

    def _on_compare_release(self):
        self._show_original = False
        self.update()

    def _on_copy_clicked(self):
        if self._translated_texts:
            QApplication.clipboard().setText("\n".join(self._translated_texts))
            self.btn_copy.setText("✓ 已复制")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 复制全部"))

    def _on_ask_clicked(self):
        full_text = "\n".join(self._translated_texts)
        win = get_ask_ai_window()
        win.set_context(
            original_text="（选区文字内容）",
            translated_text=full_text,
            extra_context=full_text
        )
        win.show_on_top()

    def _on_save_clicked(self):
        target = self._original_pil if self._show_original else (self._translated_pil or self._original_pil)
        if target:
            path, _ = QFileDialog.getSaveFileName(self, "保存选区翻译图片", "area_translated.png", "PNG (*.png);;JPG (*.jpg)")
            if path:
                target.save(path)


class AreaSnippingWindow(QWidget):
    """Full-screen snipping overlay tool with Left-click auto snip and Right-click confirm card."""

    progress_signal = pyqtSignal(str, int)
    finish_signal = pyqtSignal(object, object, list, list, object)  # (orig_pil, trans_pil, blocks, texts, rect)
    detail_translate_requested = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._full_screenshot: Optional[Image.Image] = None
        self._full_pixmap: Optional[QPixmap] = None

        self._is_dragging = False
        self._drag_button = Qt.MouseButton.LeftButton
        self._start_pos = QPoint()
        self._current_pos = QPoint()
        self._selected_rect = QRect()

        self.confirm_card = ConfirmCard(self)
        self.confirm_card.confirmed.connect(self._on_confirm_triggered)
        self.confirm_card.cancelled.connect(self._on_cancel_triggered)

        self.viewer = AreaTranslationViewer()
        self.viewer.detail_translate_requested.connect(self.detail_translate_requested)

        self.progress_signal.connect(self.viewer.update_progress)
        self.finish_signal.connect(self.viewer.display_result)

    def start_snipping(self):
        """Captures full screen and enters interactive snipping mode with fresh state."""
        self.confirm_card.hide()
        self._is_dragging = False
        self._selected_rect = QRect()

        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Capture base screen
        self._full_screenshot = screen_capture.capture_fullscreen()
        self._full_pixmap = pil_to_qpixmap(self._full_screenshot)

        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.confirm_card.hide()
            self._selected_rect = QRect()
            self._is_dragging = True
            self._drag_button = event.button()
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._is_dragging and event.button() == self._drag_button:
            self._is_dragging = False

            rx = min(self._start_pos.x(), self._current_pos.x())
            ry = min(self._start_pos.y(), self._current_pos.y())
            rw = abs(self._current_pos.x() - self._start_pos.x())
            rh = abs(self._current_pos.y() - self._start_pos.y())

            if rw < 16 or rh < 16:
                self._selected_rect = QRect()
                self.update()
                return

            self._selected_rect = QRect(rx, ry, rw, rh)

            if event.button() == Qt.MouseButton.LeftButton:
                # Left Click Release: Instant translation
                self._execute_area_translation(self._selected_rect)
            elif event.button() == Qt.MouseButton.RightButton:
                # Right Click Release: Show confirmation card
                card_x = min(self.width() - 180, rx + rw + 8)
                card_y = max(10, ry)
                self.confirm_card.move(card_x, card_y)
                self.confirm_card.show()
                self.confirm_card.raise_()
                self.update()

    def _on_confirm_triggered(self):
        self.confirm_card.hide()
        if not self._selected_rect.isEmpty():
            self._execute_area_translation(self._selected_rect)

    def _on_cancel_triggered(self):
        self.confirm_card.hide()
        self._selected_rect = QRect()
        self.update()

    def _execute_area_translation(self, rect: QRect):
        self.hide()
        if self._full_screenshot is None:
            return

        img_w = self._full_screenshot.width
        img_h = self._full_screenshot.height
        vp_w = max(1, self.width())
        vp_h = max(1, self.height())

        # Map viewport coordinates to physical image coordinates
        x0 = max(0, int((rect.x() / vp_w) * img_w))
        y0 = max(0, int((rect.y() / vp_h) * img_h))
        x1 = min(img_w, int(((rect.x() + rect.width()) / vp_w) * img_w))
        y1 = min(img_h, int(((rect.y() + rect.height()) / vp_h) * img_h))

        if x1 <= x0 or y1 <= y0:
            return

        crop_pil = self._full_screenshot.crop((x0, y0, x1, y1))
        target_lang = config_manager.get("translation", "target_language", "zh-CN")

        # Show initial cropped image and capsule progress HUD in viewer
        self.viewer.show_initial_crop(crop_pil, rect)

        def _worker():
            try:
                self.progress_signal.emit("🚀 正在调用 OCR 识别选区文字...", 20)
                blocks = ocr_engine.recognize(crop_pil)
                valid_blocks = [b for b in blocks if b.get("text", "").strip()]
                texts = [b["text"].strip() for b in valid_blocks]

                if texts:
                    self.progress_signal.emit(f"📝 OCR 识别到 {len(texts)} 处文字，正在请求 AI 翻译...", 45)

                    def _prog_cb(cur: int, total: int, msg: str):
                        pct = int(45 + 45 * (cur / max(1, total)))
                        self.progress_signal.emit(msg, pct)

                    full_ctx = "\n".join(texts)
                    translated_texts = ai_client.translate_batch_texts(
                        texts,
                        target_lang=target_lang,
                        full_context=full_ctx,
                        image_pil=crop_pil,
                        progress_callback=_prog_cb,
                    )

                    self.progress_signal.emit("🎨 正在原位重绘渲染译文...", 95)
                    rendered_img = screen_capture.render_inplace_translation(
                        crop_pil, valid_blocks, translated_texts
                    )
                else:
                    valid_blocks = []
                    translated_texts = []
                    rendered_img = crop_pil

                # Emit final image to UI thread
                self.finish_signal.emit(crop_pil, rendered_img, valid_blocks, translated_texts, rect)

            except Exception as e:
                print(f"[AreaSnipping] Worker error: {e}")
                self.finish_signal.emit(crop_pil, crop_pil, [], [], rect)

        threading.Thread(target=_worker, daemon=True).start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._selected_rect = QRect()
            self.confirm_card.hide()
            self.close()
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. Draw base full screenshot scaled to window size
        if self._full_pixmap:
            painter.drawPixmap(self.rect(), self._full_pixmap)

        # 2. Draw dark semi-transparent mask
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        # 3. Determine active rect to clear mask for
        rect_to_draw = QRect()
        if self._is_dragging:
            rx = min(self._start_pos.x(), self._current_pos.x())
            ry = min(self._start_pos.y(), self._current_pos.y())
            rw = abs(self._current_pos.x() - self._start_pos.x())
            rh = abs(self._current_pos.y() - self._start_pos.y())
            rect_to_draw = QRect(rx, ry, rw, rh)
        elif not self._selected_rect.isEmpty():
            rect_to_draw = self._selected_rect

        # 4. Pixel-perfect High DPI mask clearing and highlight drawing
        if not rect_to_draw.isEmpty() and self._full_pixmap:
            img_w = self._full_pixmap.width()
            img_h = self._full_pixmap.height()
            vp_w = max(1, self.width())
            vp_h = max(1, self.height())

            src_x = int((rect_to_draw.x() / vp_w) * img_w)
            src_y = int((rect_to_draw.y() / vp_h) * img_h)
            src_w = int((rect_to_draw.width() / vp_w) * img_w)
            src_h = int((rect_to_draw.height() / vp_h) * img_h)
            source_rect = QRect(src_x, src_y, src_w, src_h)

            # Draw clear unmasked image region inside selected box
            painter.drawPixmap(rect_to_draw, self._full_pixmap, source_rect)

            # Border color: Blue for Left click, Amber for Right click
            border_color = QColor(0, 120, 212, 240) if self._drag_button == Qt.MouseButton.LeftButton else QColor(255, 170, 0, 240)
            pen = QPen(border_color, 2, Qt.PenStyle.SolidLine if self._drag_button == Qt.MouseButton.LeftButton else Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect_to_draw)

            # Size Dimension Badge
            badge_text = f"{rect_to_draw.width()} × {rect_to_draw.height()} px"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            badge_rect = QRect(rect_to_draw.x() + 4, max(4, rect_to_draw.y() - 24), 100, 20)
            painter.fillRect(badge_rect, QColor(0, 0, 0, 180))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
