"""Windows のシステムトレイ。exe と同じアイコン（assets/icon.png と同一データ）を表示する。
pystray/Pillow が無い環境では None を返して無効化する。"""
import base64
import io
import threading


def _load_icon(Image):
    from icon_data import ICON_PNG_B64
    img = Image.open(io.BytesIO(base64.b64decode(ICON_PNG_B64))).convert("RGBA")
    return img.resize((64, 64))


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
