"""クリップボード監視（別スレッド）とグローバルホットキー（Windows のみ）。"""
import sys
import threading
import time

import pyperclip

from source_info import foreground_info

MAX_CHARS = 20000


class ClipboardMonitor(threading.Thread):
    def __init__(self, cfg, store, embed, on_new):
        super().__init__(daemon=True, name="clipboard-monitor")
        self.cfg = cfg
        self.store = store
        self.embed = embed
        self.on_new = on_new
        self._stop_evt = threading.Event()
        self._last = None
        self._last_purge = 0.0

    def mark(self, text: str) -> None:
        """アプリ自身がコピーした内容を再度保存しないようにする"""
        self._last = text

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        while not self._stop_evt.is_set():
            try:
                self._tick()
            except Exception:
                pass
            self._stop_evt.wait(0.6)

    def _tick(self) -> None:
        now = time.time()
        if now - self._last_purge > 3600:
            self.store.purge(self.cfg.retention_days)
            self._last_purge = now
        if not self.cfg.monitoring:
            return
        text = pyperclip.paste()
        if not text or text == self._last:
            return
        self._last = text
        if not text.strip():
            return
        text = text[:MAX_CHARS]
        info = foreground_info()
        app = info["app"]
        if app and any(k and k.lower() in app.lower() for k in self.cfg.ignored_apps):
            return  # パスワードマネージャーなどからのコピーは保存しない
        self.store.add(text, app, info["title"], self.embed(text))
        self.on_new()


def register_hotkey(spec: str, callback):
    if sys.platform != "win32" or not spec:
        return None
    try:
        import keyboard
    except ImportError:
        return None
    return keyboard.add_hotkey(spec, callback)


def unregister_hotkey(handle) -> None:
    if handle is None:
        return
    import keyboard
    keyboard.remove_hotkey(handle)
