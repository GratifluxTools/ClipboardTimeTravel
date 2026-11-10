"""Windows のスタートアップ登録（HKCU の Run キー）。"""
import os
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ClipboardTimeTravel"


def set_startup(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    if getattr(sys, "frozen", False):
        cmd = f'"{sys.executable}"'
    else:
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        cmd = f'"{sys.executable}" "{script}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    return True
