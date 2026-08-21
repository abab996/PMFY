import ctypes
import time
from typing import Optional

from app.utils.window_utils import is_console_window

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002

_uia_instance = None
_uia_initialized = False


def _get_uia():
    """Lazily initializes Windows UI Automation COM interface."""
    global _uia_instance, _uia_initialized
    if _uia_initialized:
        return _uia_instance
    _uia_initialized = True
    try:
        import comtypes.client
        comtypes.client.GetModule("UIAutomationCore.dll")
        import comtypes.gen.UIAutomationClient as UIA
        _uia_instance = comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation)
    except Exception as e:
        _uia_instance = None
    return _uia_instance


def get_selected_text_via_uia() -> Optional[str]:
    """Attempts to retrieve selected text directly via Windows UI Automation (zero clipboard pollution)."""
    uia = _get_uia()
    if not uia:
        return None
    try:
        import comtypes.gen.UIAutomationClient as UIA
        element = uia.GetFocusedElement()
        if not element:
            return None
        # UIA_TextPatternId = 10014
        pattern = element.GetCurrentPattern(10014)
        if pattern:
            text_pattern = pattern.QueryInterface(UIA.IUIAutomationTextPattern)
            selection_ranges = text_pattern.GetSelection()
            if selection_ranges and selection_ranges.Length > 0:
                text = selection_ranges.GetElement(0).GetText(-1)
                if text and text.strip():
                    return text.strip()
    except Exception:
        pass
    return None


def simulate_ctrl_c():
    """Simulates Ctrl+C keystroke safely using keybd_event."""
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def get_selected_text_via_clipboard(timeout: float = 0.15) -> Optional[str]:
    """
    Simulates Ctrl+C to retrieve newly selected text.
    Uses temporary clipboard clearing + restoration to ensure NO text is falsely reported on empty space.
    """
    import win32clipboard
    import win32con

    # 1. First attempt non-destructive UI Automation check
    uia_text = get_selected_text_via_uia()
    if uia_text and len(uia_text.strip()) > 0:
        return uia_text.strip()

    # 2. SAFETY GUARD: In Console / Terminal / CLI windows (cmd.exe, Windows Terminal, ConEmu, Mintty):
    # NEVER send blind Ctrl+C because Ctrl+C transmits SIGINT and terminates running CLI processes!
    fg_hwnd = user32.GetForegroundWindow()
    if is_console_window(fg_hwnd):
        return None

    # 3. Backup existing clipboard content
    old_clipboard_text = None
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old_clipboard_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        # Empty clipboard before probe
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    # 3. Simulate Ctrl+C
    simulate_ctrl_c()

    # 4. Check if active window actually populated the clipboard with new text
    start_time = time.time()
    new_text = None
    while time.time() - start_time < timeout:
        time.sleep(0.02)
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                new_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            if new_text and new_text.strip():
                break
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    # 5. If nothing was copied, restore user's old clipboard content
    if not new_text or not new_text.strip():
        if old_clipboard_text is not None:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_clipboard_text)
                win32clipboard.CloseClipboard()
            except Exception:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
        return None

    return new_text.strip()
