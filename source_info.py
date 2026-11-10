"""フォアグラウンドのウィンドウ情報（コピー元アプリ名・ウィンドウタイトル）を取得する。
Windows は ctypes（pywin32 不要）、Linux は xdotool を使う。取得できなければ空文字。"""
import ctypes
import os
import subprocess
import sys
from ctypes import wintypes


def foreground_info() -> dict:
    try:
        if sys.platform == "win32":
            return _win()
        if sys.platform.startswith("linux"):
            return _linux()
    except Exception:
        pass
    return {"app": "", "title": ""}


def _win() -> dict:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"app": "", "title": ""}
    n = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, title_buf, n + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app = ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if handle:
        try:
            size = wintypes.DWORD(1024)
            path_buf = ctypes.create_unicode_buffer(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(size)):
                app = os.path.basename(path_buf.value)
        finally:
            kernel32.CloseHandle(handle)
    return {"app": app, "title": title_buf.value}


def _linux() -> dict:
    def x(*args):
        return subprocess.run(["xdotool", *args], capture_output=True, text=True,
                              timeout=1).stdout.strip()

    title = x("getactivewindow", "getwindowname")
    pid = x("getactivewindow", "getwindowpid")
    app = ""
    if pid.isdigit():
        try:
            with open(f"/proc/{pid}/comm", encoding="utf-8") as fh:
                app = fh.read().strip()
        except OSError:
            pass
    return {"app": app, "title": title}
