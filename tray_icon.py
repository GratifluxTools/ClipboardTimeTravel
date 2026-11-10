"""Windows のシステムトレイ。実行中の exe に埋め込まれているアイコンをそのまま表示する。
取得に失敗した場合のみ、単色のアイコンを使う。pystray/Pillow が無い環境では None を返す。"""
import ctypes
import sys
import threading
from ctypes import wintypes

H = ctypes.c_void_p


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def _running_exe_path() -> str:
    k32 = ctypes.WinDLL("kernel32")
    k32.GetModuleFileNameW.argtypes = [H, ctypes.c_wchar_p, wintypes.DWORD]
    buf = ctypes.create_unicode_buffer(1024)
    k32.GetModuleFileNameW(None, buf, 1024)
    return buf.value


def _icon_from_exe(Image, size: int = 32):
    user32 = ctypes.WinDLL("user32")
    gdi32 = ctypes.WinDLL("gdi32")
    shell32 = ctypes.WinDLL("shell32")

    user32.GetDC.restype = H
    user32.GetDC.argtypes = [H]
    user32.ReleaseDC.argtypes = [H, H]
    user32.DrawIconEx.argtypes = [H, ctypes.c_int, ctypes.c_int, H,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_uint, H, ctypes.c_uint]
    user32.DrawIconEx.restype = wintypes.BOOL
    user32.DestroyIcon.argtypes = [H]
    gdi32.CreateCompatibleDC.restype = H
    gdi32.CreateCompatibleDC.argtypes = [H]
    gdi32.CreateDIBSection.restype = H
    gdi32.CreateDIBSection.argtypes = [H, ctypes.POINTER(_BITMAPINFOHEADER), ctypes.c_uint,
                                       ctypes.POINTER(H), H, wintypes.DWORD]
    gdi32.SelectObject.restype = H
    gdi32.SelectObject.argtypes = [H, H]
    gdi32.DeleteObject.argtypes = [H]
    gdi32.DeleteDC.argtypes = [H]
    shell32.ExtractIconExW.restype = wintypes.UINT
    shell32.ExtractIconExW.argtypes = [ctypes.c_wchar_p, ctypes.c_int,
                                       ctypes.POINTER(H), ctypes.POINTER(H), wintypes.UINT]

    large = H()
    if shell32.ExtractIconExW(_running_exe_path(), 0, ctypes.byref(large), None, 1) < 1 or not large.value:
        return None
    screen = mem = dib = None
    try:
        bmi = _BITMAPINFOHEADER(ctypes.sizeof(_BITMAPINFOHEADER), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
        screen = user32.GetDC(None)
        mem = gdi32.CreateCompatibleDC(screen)
        bits = H()
        dib = gdi32.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        old = gdi32.SelectObject(mem, dib)
        ctypes.memset(bits.value, 0, size * size * 4)
        user32.DrawIconEx(mem, 0, 0, large, size, size, 0, None, 3)  # DI_NORMAL
        data = ctypes.string_at(bits.value, size * size * 4)
        gdi32.SelectObject(mem, old)
        return Image.frombuffer("RGBA", (size, size), data, "raw", "BGRA", 0, 1).copy()
    finally:
        if dib:
            gdi32.DeleteObject(dib)
        if mem:
            gdi32.DeleteDC(mem)
        if screen:
            user32.ReleaseDC(None, screen)
        user32.DestroyIcon(large)


def _load_icon(Image):
    if sys.platform == "win32":
        try:
            img = _icon_from_exe(Image)
            if img is not None:
                return img
        except Exception:
            pass
    return Image.new("RGBA", (32, 32), (37, 99, 235, 255))


def start_tray(title, labels, on_open, on_toggle_monitor, on_quit, is_monitoring):
    try:
        import pystray
        from PIL import Image
    except Exception:
        return None
    menu = pystray.Menu(
        pystray.MenuItem(labels["open"], lambda icon, item: on_open(), default=True),
        pystray.MenuItem(labels["monitor"], lambda icon, item: on_toggle_monitor(),
                         checked=lambda item: is_monitoring()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(labels["quit"], lambda icon, item: on_quit()),
    )
    icon = pystray.Icon("clipboard_time_travel", _load_icon(Image), title, menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon
