"""多重起動の防止。二つ目のプロセスが動くと、同じクリップボードを二重に保存してしまうため、
起動中のアプリがあればそのウィンドウを前面に出して終了する。
Windows は名前付きミューテックス、それ以外は flock を使う。"""
import ctypes
import os
import sys
import time

_held = None  # プロセス終了まで保持してロックを維持する
WINDOW_TITLE = "Clipboard Time Travel"


def _try_acquire(data_dir: str) -> bool:
    global _held
    if sys.platform == "win32":
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        handle = k32.CreateMutexW(None, False, "Local\\ClipboardTimeTravelSingleton")
        if not handle:
            return False
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            k32.CloseHandle(ctypes.c_void_p(handle))
            return False
        _held = handle
        return True
    import fcntl
    fd = os.open(os.path.join(data_dir, "instance.lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    _held = fd
    return True


def acquire(data_dir: str, wait_seconds: float = 0.0) -> bool:
    """起動権を取得できれば True。再起動直後など、前のプロセスが終わるまで待つ場合は wait_seconds を指定する。"""
    deadline = time.time() + wait_seconds
    while True:
        if _try_acquire(data_dir):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.3)


def activate_existing_window() -> None:
    """既に起動中のウィンドウ（トレイ格納中を含む）を表示して前面に出す。Windows のみ。"""
    if sys.platform != "win32":
        return
    u32 = ctypes.WinDLL("user32")
    u32.FindWindowW.restype = ctypes.c_void_p
    u32.FindWindowW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    u32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    u32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    hwnd = u32.FindWindowW(None, WINDOW_TITLE)
    if hwnd:
        u32.ShowWindow(hwnd, 5)  # SW_SHOW
        u32.SetForegroundWindow(hwnd)
