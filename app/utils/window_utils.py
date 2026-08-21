import ctypes
from typing import Optional, Tuple

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


# Win32 Hit-Test Constants (WM_NCHITTEST)
HTERROR = -2
HTTRANSPARENT = -1
HTNOWHERE = 0
HTCLIENT = 1
HTCAPTION = 2
HTSYSMENU = 3
HTGROWBOX = 4
HTSIZE = 4
HTMENU = 5
HTHSCROLL = 6
HTVSCROLL = 7
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTBORDER = 18
HTCLOSE = 20
HTHELP = 21

# Known Windows Shell and desktop window classes to ignore for text selection
SHELL_CLASS_NAMES = {
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Progman",
    "WorkerW",
    "DV2ControlHost",
    "Windows.UI.Core.CoreWindow",
    "TopLevelWindowForOverflowXamlIsland",
    "TrayNotifyWnd",
    "MSTaskSwWClass",
}

# Known Terminal / Console window classes
CONSOLE_CLASS_NAMES = {
    "ConsoleWindowClass",
    "CASCADIA_HOSTING_WINDOW_CLASS",  # Windows Terminal
    "VirtualConsoleClass",            # ConEmu
    "Mintty",                         # Git Bash / Cygwin
    "PuTTY",
    "X410_X11_WindowClass",
}


def get_window_class_name(hwnd: int) -> str:
    """Returns the window class name for a given HWND."""
    if not hwnd:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Returns (left, top, right, bottom) for a given HWND."""
    if not hwnd:
        return None
    try:
        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        pass
    return None


def get_window_hit_test(hwnd: int, x: int, y: int) -> int:
    """
    Performs a non-blocking WM_NCHITTEST (0x0084) on the window at (x, y).
    Returns 1 (HTCLIENT) if in the content/client area,
    or other values (like 2 for HTCAPTION, 18 for HTBORDER, etc.) if in non-client area.
    """
    if not hwnd:
        return HTNOWHERE
    try:
        lparam = (int(y) << 16) | (int(x) & 0xFFFF)
        result = ctypes.c_ulong()
        # SendMessageTimeoutW with SMTO_ABORTIFHUNG (0x0002) and 60ms timeout
        res = user32.SendMessageTimeoutW(
            hwnd,
            0x0084,  # WM_NCHITTEST
            0,
            lparam,
            0x0002,  # SMTO_ABORTIFHUNG
            60,
            ctypes.byref(result),
        )
        if res:
            return result.value
    except Exception:
        pass
    return HTCLIENT


def get_window_info_at(x: int, y: int):
    """
    Returns (hwnd, root_hwnd, class_name, root_rect, hit_test) for the point (x, y).
    """
    pt = POINT(int(x), int(y))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return 0, 0, "", None, HTNOWHERE

    # GA_ROOT = 2 (retrieves the root window by walking the chain of parent windows)
    root_hwnd = user32.GetAncestor(hwnd, 2)
    if not root_hwnd:
        root_hwnd = hwnd

    class_name = get_window_class_name(root_hwnd) or get_window_class_name(hwnd)
    root_rect = get_window_rect(root_hwnd)
    hit_test = get_window_hit_test(hwnd, x, y)

    return hwnd, root_hwnd, class_name, root_rect, hit_test


def is_console_window(hwnd: int) -> bool:
    """Checks if the given window or its root is a known console/terminal window."""
    if not hwnd:
        return False
    cls = get_window_class_name(hwnd)
    if cls in CONSOLE_CLASS_NAMES:
        return True
    root = user32.GetAncestor(hwnd, 2)
    if root and root != hwnd:
        root_cls = get_window_class_name(root)
        if root_cls in CONSOLE_CLASS_NAMES:
            return True
    return False
