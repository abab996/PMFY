from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget
from qfluentwidgets import Action, RoundMenu

from app.config import config_manager


def create_tray_icon_pixmap() -> QPixmap:
    """Dynamically renders a crisp Windows 11 style blue '译' tray icon."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center = size / 2.0
    radius = size / 2.0 - 3.0

    # Gradient Background
    gradient = QLinearGradient(0, 0, 0, size)
    gradient.setColorAt(0.0, QColor("#1E90FF"))
    gradient.setColorAt(1.0, QColor("#0078D4"))

    path = QPainterPath()
    path.addEllipse(QPointF(center, center), radius, radius)
    painter.fillPath(path, QBrush(gradient))

    # Border
    painter.setPen(QPen(QColor(255, 255, 255, 200), 2.5))
    painter.drawPath(path)

    # Character '译'
    painter.setPen(QColor(255, 255, 255, 250))
    font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    painter.setFont(font)
    painter.drawText(
        QRectF(0, 0, size, size),
        Qt.AlignmentFlag.AlignCenter,
        "译",
    )
    painter.end()

    return pixmap


class SystemTray(QSystemTrayIcon):
    """Windows 11 System Tray Icon."""

    open_settings_requested = pyqtSignal()
    fullscreen_translate_requested = pyqtSignal()
    selection_toggled = pyqtSignal(bool)
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(create_tray_icon_pixmap()))
        self.setToolTip("PMFY 全局翻译 (双击打开软件设置)")

        self._init_menu()
        self.activated.connect(self._on_activated)

    def _init_menu(self):
        # Create context menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                color: #201F1E;
            }
            QMenu::item:selected {
                background-color: #EDEBE9;
            }
            QMenu::separator {
                height: 1px;
                background-color: #EDEBE9;
                margin: 4px 6px;
            }
        """)

        # Actions
        act_settings = self.menu.addAction("⚙️ 打开设置中心")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        act_fs = self.menu.addAction("🔍 立即全屏翻译 (Ctrl+Win+Alt)")
        act_fs.triggered.connect(self.fullscreen_translate_requested.emit)

        self.menu.addSeparator()

        # Selection translation toggle action
        self.act_sel_toggle = self.menu.addAction("🔘 划词悬停翻译")
        self.act_sel_toggle.setCheckable(True)
        is_sel_enabled = config_manager.get("selection", "enabled", True)
        self.act_sel_toggle.setChecked(is_sel_enabled)
        self.act_sel_toggle.toggled.connect(self._on_selection_toggled)

        self.menu.addSeparator()

        act_exit = self.menu.addAction("❌ 退出程序")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(self.menu)

    def _on_selection_toggled(self, checked: bool):
        config_manager.set("selection", "enabled", checked)
        self.selection_toggled.emit(checked)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click also provides friendly response or menu
            pass
