import ctypes
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from app.main_app import PMFYApplication
from app.ui.tray_icon import create_tray_icon_pixmap

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "PMFY_GLOBAL_TRANSLATOR_MUTEX_V1"


def acquire_single_instance_lock():
    """Acquires a Windows Named Mutex to prevent multiple instances from running concurrently."""
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    if last_error == ERROR_ALREADY_EXISTS:
        return False, mutex
    return True, mutex


def setup_windows_dpi_and_app_id():
    """Sets up custom AppUserModelID for Windows taskbar grouping."""
    try:
        myappid = "pmfy.global.translator.win11.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


def main():
    # Single Instance Check
    is_first_instance, mutex = acquire_single_instance_lock()
    if not is_first_instance:
        print("[PMFY] 检测到程序已在后台运行中，本次启动已自动取消。")
        try:
            # Show a native top-most Windows notification box
            ctypes.windll.user32.MessageBoxW(
                0,
                "PMFY 全局翻译软件已经在后台运行中！\n\n请在屏幕右下角任务栏托盘区域查看蓝色【译】图标。\n双击托盘图标可打开设置中心，或直接按 Ctrl+Win+Alt 进行全屏翻译。",
                "PMFY 运行提示",
                0x00000040 | 0x00040000  # MB_ICONINFORMATION | MB_TOPMOST
            )
        except Exception:
            pass
        sys.exit(0)

    setup_windows_dpi_and_app_id()

    # Enable High DPI scaling
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("PMFY 全局翻译")
    app.setOrganizationName("PMFY")
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    # Set default app font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    # Set default app icon
    ico_path = os.path.join(os.path.dirname(__file__), "app", "resources", "icon.ico")
    if os.path.exists(ico_path):
        app_icon = QIcon(ico_path)
    else:
        app_icon = QIcon(create_tray_icon_pixmap())
    app.setWindowIcon(app_icon)

    # Create Main Application Coordinator
    pmfy_app = PMFYApplication(app)

    print("=" * 60)
    print("🚀 PMFY 全局翻译桌面应用已成功启动！")
    print("📌 托盘图标：已常驻任务栏右下角通知区域 (双击可打开设置)")
    print("🔘 划词翻译：鼠标框选文字后释放，悬停在蓝色小圆圈上即可翻译")
    print("⌨️ 全屏翻译：默认快捷键 Ctrl+Win+Alt 立即原位翻译整个屏幕")
    print("=" * 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
