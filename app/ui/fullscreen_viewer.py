import io
import os
import threading
import time
from typing import Any, Dict, List, Optional

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
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
from qfluentwidgets import ComboBox, ProgressBar

from app.config import config_manager
from app.core.ai_client import ai_client
from app.core.ocr_engine import ocr_engine
from app.core.screen_capture import screen_capture
from app.ui.ask_ai_window import get_ask_ai_window
from app.ui.theme import ACCENT_COLOR


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    qimg = QImage()
    qimg.loadFromData(img_byte_arr.getvalue())
    return QPixmap.fromImage(qimg)


class SelectionTooltipBar(QFrame):
    """Mini floating toolbar that appears when user selects a region on the fullscreen image."""

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


class FullscreenViewer(QWidget):
    """Full-screen interactive viewer for in-place translated screen images."""

    # Threading signals
    status_updated = pyqtSignal(str, int)
    translation_completed = pyqtSignal(object, object, list, list)
    translation_error = pyqtSignal(str)
    detail_translate_requested = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._original_pil: Optional[Image.Image] = None
        self._translated_pil: Optional[Image.Image] = None
        self._original_pixmap: Optional[QPixmap] = None
        self._translated_pixmap: Optional[QPixmap] = None
        self._ocr_blocks: List[Dict[str, Any]] = []
        self._translated_texts: List[str] = []

        self._show_original: bool = False
        self._is_processing: bool = False

        # Pan & Zoom
        self._scale: float = 1.0
        self._pan_offset = QPointF(0, 0)
        self._is_panning: bool = False
        self._pan_start_pos = QPoint()

        # Left Drag Selection
        self._is_selecting: bool = False
        self._selection_start = QPoint()
        self._selection_end = QPoint()

        self.lang_map: Dict[str, str] = {
            "简体中文": "zh-CN",
            "繁體中文": "zh-TW",
            "English": "en",
            "日本語": "ja",
            "한국어": "ko",
            "Français": "fr",
            "Deutsch": "de",
            "Español": "es",
        }

        self._init_ui()

        self.status_updated.connect(self._on_status_update)
        self.translation_completed.connect(self._on_translation_completed)
        self.translation_error.connect(self._on_translation_error)

    def _init_ui(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Top Floating Win11 Acrylic Pill Toolbar
        self.toolbar = QFrame(self)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 20px;
            }
            QPushButton {
                background-color: transparent;
                color: #201F1E;
                font-size: 13px;
                font-weight: 500;
                border: none;
                border-radius: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.06); }
            QPushButton:pressed { background-color: rgba(0, 0, 0, 0.12); }
        """)

        tb_shadow = QGraphicsDropShadowEffect(self)
        tb_shadow.setBlurRadius(20)
        tb_shadow.setColor(QColor(0, 0, 0, 40))
        tb_shadow.setOffset(0, 4)
        self.toolbar.setGraphicsEffect(tb_shadow)

        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(12, 6, 12, 6)
        tb_layout.setSpacing(8)

        self.status_badge = QLabel("✨ 全屏原位翻译", self.toolbar)
        self.status_badge.setStyleSheet(f"""
            background-color: #EFF6FC;
            color: {ACCENT_COLOR};
            font-size: 12px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 10px;
        """)
        tb_layout.addWidget(self.status_badge)

        self.lang_combo = ComboBox(self.toolbar)
        self.lang_combo.addItems(list(self.lang_map.keys()))
        self.lang_combo.setFixedWidth(110)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)
        tb_layout.addWidget(self.lang_combo)

        self.btn_compare = QPushButton("👁️ 按住对比原图", self.toolbar)
        self.btn_compare.pressed.connect(self._start_compare)
        self.btn_compare.released.connect(self._stop_compare)
        tb_layout.addWidget(self.btn_compare)

        self.btn_ask_ai = QPushButton("🤖 问 AI", self.toolbar)
        self.btn_ask_ai.setStyleSheet("color: #0078D4; font-weight: bold;")
        self.btn_ask_ai.clicked.connect(self._on_top_ask_ai_clicked)
        tb_layout.addWidget(self.btn_ask_ai)

        self.btn_copy_all = QPushButton("📋 复制全部", self.toolbar)
        self.btn_copy_all.clicked.connect(self._copy_all_text)
        tb_layout.addWidget(self.btn_copy_all)

        self.btn_save = QPushButton("💾 保存图片", self.toolbar)
        self.btn_save.clicked.connect(self._save_image)
        tb_layout.addWidget(self.btn_save)

        self.btn_reset_zoom = QPushButton("🔍 还原大小", self.toolbar)
        self.btn_reset_zoom.clicked.connect(self._reset_zoom)
        tb_layout.addWidget(self.btn_reset_zoom)

        self.btn_close = QPushButton("✕ 关闭 (ESC)", self.toolbar)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #FDE7E9;
                color: #A80000;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FCD0D5; }
        """)
        self.btn_close.clicked.connect(self.close)
        tb_layout.addWidget(self.btn_close)

        layout.addWidget(self.toolbar, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        # Lowered Center Status HUD with Dynamic Progress Bar
        self.hud_card = QFrame(self)
        self.hud_card.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 28, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 16px;
            }
        """)
        hud_shadow = QGraphicsDropShadowEffect(self)
        hud_shadow.setBlurRadius(30)
        hud_shadow.setColor(QColor(0, 0, 0, 90))
        self.hud_card.setGraphicsEffect(hud_shadow)

        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(24, 16, 24, 16)
        hud_layout.setSpacing(10)

        self.hud_label = QLabel("🚀 正在捕获屏幕并调用 OCR 识别文字...", self.hud_card)
        self.hud_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 600;")
        self.hud_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hud_layout.addWidget(self.hud_label)

        self.hud_progress = ProgressBar(self.hud_card)
        self.hud_progress.setValue(10)
        self.hud_progress.setFixedHeight(6)
        hud_layout.addWidget(self.hud_progress)

        self.hud_card.setFixedSize(460, 84)
        self.hud_card.hide()

        # Floating Mini Tooltip Bar for selection
        self.selection_bar = SelectionTooltipBar(self)
        self.selection_bar.translate_clicked.connect(self._on_bar_translate)
        self.selection_bar.ask_ai_clicked.connect(self._on_bar_ask_ai)

    def start_fullscreen_translation(self):
        if self._is_processing or self.isVisible():
            return

        self._is_processing = True
        self._reset_zoom()
        self.selection_bar.hide()

        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        cfg_lang = config_manager.get("translation", "target_language", "zh-CN")
        for name, code in self.lang_map.items():
            if code == cfg_lang:
                self.lang_combo.blockSignals(True)
                self.lang_combo.setCurrentText(name)
                self.lang_combo.blockSignals(False)
                break

        orig_img = screen_capture.capture_fullscreen()
        self._original_pil = orig_img
        self._original_pixmap = pil_to_qpixmap(orig_img)
        self._translated_pixmap = None

        hud_x = (self.width() - self.hud_card.width()) // 2
        hud_y = int(self.height() * 0.70)
        self.hud_card.move(hud_x, hud_y)
        self.hud_label.setText("🔍 正在使用 RapidOCR 分析屏幕文字与位置...")
        self.hud_progress.setValue(15)
        self.hud_card.show()
        self.hud_card.raise_()
        self.toolbar.show()
        self.toolbar.raise_()

        self.showFullScreen()
        self.raise_()
        self.activateWindow()

        target_lang = self.lang_map.get(self.lang_combo.currentText(), "zh-CN")
        threading.Thread(
            target=self._process_translation_pipeline,
            args=(orig_img, target_lang),
            daemon=True,
        ).start()

    def _process_translation_pipeline(self, orig_img: Image.Image, target_lang: str):
        try:
            self.status_updated.emit("🔍 正在精准识别屏幕文字与坐标...", 25)
            blocks = ocr_engine.recognize(orig_img)

            if not blocks:
                self.status_updated.emit("⚠️ 屏幕上未识别到有效文字内容", 100)
                time.sleep(1.0)
                self.translation_completed.emit(orig_img, orig_img, [], [])
                return

            texts = [b["text"] for b in blocks]
            full_context = "\n".join(texts)

            def _progress_cb(curr, total, msg):
                pct = 30 + int((curr / max(1, total)) * 55)
                self.status_updated.emit(f"🤖 AI 批处理翻译中 ({curr}/{total})...", pct)

            self.status_updated.emit(f"🤖 识别到 {len(texts)} 处文本，AI 上下文批处理翻译中...", 30)

            translated_texts = ai_client.translate_batch_texts(
                texts,
                target_lang=target_lang,
                full_context=full_context,
                image_pil=orig_img,
                progress_callback=_progress_cb,
            )

            self.status_updated.emit("🎨 正在智能背景修复并原位重绘译文...", 90)
            translated_img = screen_capture.render_inplace_translation(
                orig_img, blocks, translated_texts
            )

            self.status_updated.emit("✅ 翻译完成", 100)
            self.translation_completed.emit(orig_img, translated_img, translated_texts, blocks)

        except Exception as e:
            self.translation_error.emit(str(e))

    def _on_status_update(self, text: str, pct: int):
        self.hud_label.setText(text)
        self.hud_progress.setValue(pct)
        self.status_badge.setText(f"⚡ {text[:16]}")

    def _on_translation_completed(self, orig_img: Image.Image, trans_img: Image.Image, texts: list, blocks: list):
        self._is_processing = False
        self._original_pil = orig_img
        self._translated_pil = trans_img
        self._original_pixmap = pil_to_qpixmap(orig_img)
        self._translated_pixmap = pil_to_qpixmap(trans_img)
        self._translated_texts = texts
        self._ocr_blocks = blocks

        self.hud_card.hide()
        self.status_badge.setText("✅ 翻译完成 (右键拖动/左键框选/按住空格对比)")
        self.update()

    def _on_translation_error(self, error: str):
        self._is_processing = False
        self.hud_label.setText(f"❌ 错误: {error}")
        self.hud_progress.setValue(0)
        QTimer.singleShot(2500, self.hud_card.hide)

    def _on_lang_combo_changed(self):
        if self._original_pil and not self._is_processing:
            target_lang = self.lang_map.get(self.lang_combo.currentText(), "zh-CN")
            self._is_processing = True
            self.hud_card.show()
            self.hud_label.setText(f"⚡ 正在切换目标语言为【{self.lang_combo.currentText()}】...")
            self.hud_progress.setValue(20)
            threading.Thread(
                target=self._process_translation_pipeline,
                args=(self._original_pil, target_lang),
                daemon=True,
            ).start()

    def _start_compare(self):
        self._show_original = True
        self.update()

    def _stop_compare(self):
        self._show_original = False
        self.update()

    def _copy_all_text(self):
        if self._translated_texts:
            full_text = "\n".join(self._translated_texts)
            QApplication.clipboard().setText(full_text)
            self.btn_copy_all.setText("✓ 已复制")
            QTimer.singleShot(1500, lambda: self.btn_copy_all.setText("📋 复制全部"))

    def _save_image(self):
        target = self._original_pil if self._show_original else (self._translated_pil or self._original_pil)
        if target:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存翻译后屏幕截图", "screenshot_translated.png", "PNG 图像 (*.png);;JPEG 图像 (*.jpg)"
            )
            if file_path:
                target.save(file_path)

    def _reset_zoom(self):
        self._scale = 1.0
        self._pan_offset = QPointF(0, 0)
        self.update()

    def _on_top_ask_ai_clicked(self):
        full_context = "\n".join(self._translated_texts)
        win = get_ask_ai_window()
        win.set_context(
            original_text="（全屏所有文字内容）",
            translated_text=full_context[:500],
            extra_context=full_context
        )
        win.show_on_top()

    def _on_bar_translate(self, text: str, pos_x: int, pos_y: int):
        self.selection_bar.hide()
        # Emit signal to main application to open translation popup
        self.detail_translate_requested.emit(text, pos_x, pos_y)

    def _on_bar_ask_ai(self, text: str):
        self.selection_bar.hide()
        win = get_ask_ai_window()
        win.set_context(original_text=text, extra_context="\n".join(self._translated_texts))
        win.show_on_top()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Space:
            self._start_compare()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._stop_compare()
        super().keyReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self._scale = min(self._scale * 1.12, 4.0)
        else:
            self._scale = max(self._scale / 1.12, 0.5)
        self.selection_bar.hide()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Right Click: Pan
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.selection_bar.hide()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Left Click: Selection Box
            self._is_selecting = True
            self._selection_start = event.pos()
            self._selection_end = event.pos()
            self.selection_bar.hide()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            self._pan_offset += QPointF(delta.x(), delta.y())
            self.update()
        elif self._is_selecting:
            self._selection_end = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._handle_selection_finished()
            self.update()
        super().mouseReleaseEvent(event)

    def _handle_selection_finished(self):
        # Calculate selected rect in screen viewport
        rx = min(self._selection_start.x(), self._selection_end.x())
        ry = min(self._selection_start.y(), self._selection_end.y())
        rw = abs(self._selection_end.x() - self._selection_start.x())
        rh = abs(self._selection_end.y() - self._selection_start.y())

        if rw < 10 or rh < 10 or self._original_pil is None:
            self.selection_bar.hide()
            return

        # Viewport rendering geometry
        pw = self.width() * self._scale
        ph = self.height() * self._scale
        px = (self.width() - pw) / 2.0 + self._pan_offset.x()
        py = (self.height() - ph) / 2.0 + self._pan_offset.y()

        img_w = self._original_pil.width
        img_h = self._original_pil.height

        # Map viewport rect (rx, ry, rw, rh) back to original PIL image coordinates
        img_x0 = max(0, int(((rx - px) / pw) * img_w))
        img_y0 = max(0, int(((ry - py) / ph) * img_h))
        img_x1 = min(img_w, int(((rx + rw - px) / pw) * img_w))
        img_y1 = min(img_h, int(((ry + rh - py) / ph) * img_h))

        if img_x1 <= img_x0 or img_y1 <= img_y0:
            self.selection_bar.hide()
            return

        # 1. Match intersecting blocks from OCR block cache
        matching_blocks = []
        for i, b in enumerate(self._ocr_blocks):
            bx, by, bw, bh = b["rect"]
            bx1, by1 = bx + bw, by + bh

            # Check overlap between [img_x0, img_y0, img_x1, img_y1] and [bx, by, bx1, by1]
            inter_x = max(0, min(img_x1, bx1) - max(img_x0, bx))
            inter_y = max(0, min(img_y1, by1) - max(img_y0, by))
            if inter_x > 0 and inter_y > 0:
                # Text: use original text or translated text based on display
                text = self._translated_texts[i] if (i < len(self._translated_texts) and self._translated_texts[i]) else b["text"]
                matching_blocks.append((by, bx, text))

        # Sort blocks by Y (top to bottom), then X (left to right)
        matching_blocks.sort(key=lambda item: (item[0], item[1]))
        found_texts = [item[2] for item in matching_blocks]

        # 2. If no pre-cached blocks intersected, run on-demand local OCR crop fallback
        if not found_texts and (img_x1 - img_x0 > 15) and (img_y1 - img_y0 > 15):
            try:
                crop = self._original_pil.crop((img_x0, img_y0, img_x1, img_y1))
                crop_blocks = ocr_engine.recognize(crop)
                found_texts = [cb["text"] for cb in crop_blocks if cb.get("text")]
            except Exception as e:
                print(f"[FullscreenViewer] Crop OCR error: {e}")

        selected_str = "\n".join(found_texts).strip()

        if selected_str:
            # Position tooltip bar at top-right of user's selection box
            bar_x = max(10, min(self.width() - 240, rx + rw - 120))
            bar_y = max(50, ry - 42)
            self.selection_bar.show_for_text(selected_str, QPoint(bar_x, bar_y))
        else:
            self.selection_bar.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor(20, 20, 20, 255))

        pixmap = self._original_pixmap if self._show_original else (self._translated_pixmap or self._original_pixmap)
        if pixmap and not pixmap.isNull():
            base_w = self.width()
            base_h = self.height()
            pw = base_w * self._scale
            ph = base_h * self._scale
            px = (self.width() - pw) / 2.0 + self._pan_offset.x()
            py = (self.height() - ph) / 2.0 + self._pan_offset.y()

            target_rect = QRectF(px, py, pw, ph)
            painter.drawPixmap(target_rect.toRect(), pixmap)

        # Draw Selection Box if user is dragging left mouse
        if self._is_selecting:
            rx = min(self._selection_start.x(), self._selection_end.x())
            ry = min(self._selection_start.y(), self._selection_end.y())
            rw = abs(self._selection_end.x() - self._selection_start.x())
            rh = abs(self._selection_end.y() - self._selection_start.y())

            sel_rect = QRectF(rx, ry, rw, rh)
            painter.fillRect(sel_rect, QColor(0, 120, 212, 40))
            pen = QPen(QColor(0, 120, 212, 220), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(sel_rect)
