"""Windows のシステムトレイ。pystray/Pillow が無い環境では None を返して無効化する。"""
import threading


def _make_icon(Image, ImageDraw):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(37, 99, 235, 255))
    white = (255, 255, 255, 255)
    d.ellipse((14, 14, 50, 50), outline=white, width=4)
    d.line((32, 32, 32, 20), fill=white, width=4)
    d.line((32, 32, 42, 36), fill=white, width=4)
    return img


def start_tray(title, labels, on_open, on_toggle_monitor, on_quit, is_monitoring):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return None
    menu = pystray.Menu(
        pystray.MenuItem(labels["open"], lambda icon, item: on_open(), default=True),
        pystray.MenuItem(labels["monitor"], lambda icon, item: on_toggle_monitor(),
                         checked=lambda item: is_monitoring()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(labels["quit"], lambda icon, item: on_quit()),
    )
    icon = pystray.Icon("clipboard_time_travel", _make_icon(Image, ImageDraw), title, menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon
