import os
import sys
import winreg
from pathlib import Path

REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "PMFY"


def get_launch_command() -> str:
    root_dir = Path(__file__).resolve().parent.parent.parent
    bat_path = root_dir / "启动软件.bat"
    if bat_path.exists():
        return f'"{bat_path}"'
    run_py = root_dir / "run.py"
    return f'"{sys.executable}" "{run_py}"'


def is_autostart_enabled() -> bool:
    """Checks if PMFY is registered in Windows startup registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Enables or disables PMFY automatic startup on Windows boot."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[AutoStart] Failed to set autostart: {e}")
        return False
