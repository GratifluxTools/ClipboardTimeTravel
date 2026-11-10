import os
import subprocess
import sys
import threading

import flet as ft

from ai_engine import Embedder, ask_ollama, keyword_search, list_ollama_models, semantic_search
from app_version import __version__
from config import RETENTION_CHOICES, Config, data_dir
from crypto_utils import Vault
from i18n import set_language, t
from monitor import ClipboardMonitor, register_hotkey, unregister_hotkey
from startup import set_startup
from single_instance import acquire as acquire_instance, activate_existing_window
from storage import HistoryStore, fmt_time
from tray_icon import start_tray
from updater import REPO_URL, check_latest

IS_WINDOWS = sys.platform == "win32"
PREVIEW_LINES = 2
GREY = ft.Colors.GREY
RETENTION_KEYS = {1: "ret_1d", 7: "ret_7d", 30: "ret_30d", 90: "ret_90d", 365: "ret_1y", 0: "ret_forever"}


def svg_button(name, tooltip, on_click, size=18):
    return ft.IconButton(
        content=ft.Image(src=f"icons/{name}.svg", width=size, height=size),
        tooltip=tooltip,
        on_click=on_click,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )


def main(page: ft.Page):
    page.title = "Clipboard Time Travel"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 10

    ddir = data_dir()
    cfg_path = os.path.join(ddir, "config.json")
    cfg = Config.load(cfg_path)
    set_language(cfg.language)

    try:
        vault = Vault(os.path.join(ddir, "key.bin"))
    except Exception as ex:
        page.add(ft.Text(t("key_error", ex=ex), color=ft.Colors.RED))
        return
    store = HistoryStore(os.path.join(ddir, "history.db"), vault)
    store.purge(cfg.retention_days)
    store.dedupe_consecutive()
    embedder = Embedder(cfg.model_dir) if (cfg.semantic and cfg.model_dir) else None

    def use_semantic():
        return embedder is not None and embedder.ok

    def embed(text):
        return embedder.encode(text) if use_semantic() else None

    def snack(msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    expanded = set()

    # ---------- 履歴カード（省スペース。「表示を拡大」で全文を表示） ----------
    def copy_entry(e):
        monitor.mark(e["text"])
        page.set_clipboard(e["text"])
        snack(t("copied"))

    def delete_entry(rid):
        store.delete(rid)
        expanded.discard(rid)
        refresh_timeline()
        results.controls = [c for c in results.controls if getattr(c, "data", None) != rid]
        page.update()

    def entry_card(e):
        rid = e["id"]
        is_open = rid in expanded
        body = ft.Text(e["text"], selectable=True, overflow=ft.TextOverflow.ELLIPSIS,
                       max_lines=None if is_open else PREVIEW_LINES)
        window_line = ft.Text(e["window"], size=11, color=GREY, max_lines=1,
                              overflow=ft.TextOverflow.ELLIPSIS, visible=is_open)
        toggle_img = ft.Image(src=f"icons/{'collapse' if is_open else 'expand'}.svg", width=16, height=16)
        toggle_btn = ft.IconButton(
            content=toggle_img,
            tooltip=t("collapse") if is_open else t("expand"),
            style=ft.ButtonStyle(padding=ft.padding.all(4)),
        )

        def toggle(_):
            if rid in expanded:
                expanded.discard(rid)
            else:
                expanded.add(rid)
            now_open = rid in expanded
            body.max_lines = None if now_open else PREVIEW_LINES
            window_line.visible = now_open
            toggle_img.src = f"icons/{'collapse' if now_open else 'expand'}.svg"
            toggle_btn.tooltip = t("collapse") if now_open else t("expand")
            page.update()

        toggle_btn.on_click = toggle
        return ft.Container(
            data=rid,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE)),
            content=ft.Column(spacing=0, tight=True, controls=[
                ft.Row(spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Text(fmt_time(e["time"]), size=11, color=GREY),
                    ft.Text(e["app"] or t("unknown_app"), size=12, weight=ft.FontWeight.BOLD,
                            expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    toggle_btn,
                    svg_button("copy", t("copy"), lambda _, x=e: copy_entry(x), size=16),
                    svg_button("trash", t("delete"), lambda _, r=rid: delete_entry(r), size=16),
                ]),
                window_line,
                body,
            ]),
        )

    # ---------- タイムライン ----------
    timeline = ft.ListView(expand=True, spacing=6)

    def refresh_timeline():
        items = store.recent(300)
        timeline.controls = [entry_card(e) for e in items] or [ft.Text(t("empty_timeline"))]
        page.update()

    # ---------- 検索・チャット ----------
    def find(q, k):
        if use_semantic():
            return semantic_search(embedder, store, q, k), "mode_semantic"
        return keyword_search(store, q, k), "mode_keyword"

    query = ft.TextField(hint_text=t("search_hint"), expand=True)
    mode_text = ft.Text(size=12, color=GREY)
    results = ft.ListView(expand=True, spacing=6)

    def do_search(_=None):
        q = (query.value or "").strip()
        if not q:
            return
        items, mode_key = find(q, 5 if use_semantic() else 20)
        mode_text.value = t("results_count", mode=t(mode_key), n=len(items))
        results.controls = [entry_card(e) for e in items] or [ft.Text(t("no_results"))]
        page.update()

    query.on_submit = do_search

    def bubble(text, mine=False):
        return ft.Container(
            content=ft.Text(text, selectable=True),
            padding=10,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLUE if mine else ft.Colors.GREY),
            alignment=ft.alignment.center_right if mine else ft.alignment.center_left,
        )

    chat_log = ft.ListView(expand=True, spacing=8, auto_scroll=True)
    chat_in = ft.TextField(hint_text=t("chat_hint"), expand=True)

    def chat_context(question):
        n = max(1, int(cfg.ollama_context_count))
        matched, _mode = find(question, n)
        matched = matched[:n]
        seen = {e["id"] for e in matched}
        recent = [e for e in store.recent(n) if e["id"] not in seen]
        return matched, (matched + recent)[:n]

    def do_chat(_=None):
        question = (chat_in.value or "").strip()
        if not question:
            return
        chat_in.value = ""
        chat_log.controls.append(bubble(question, mine=True))
        matched, ctx = chat_context(question)
        if not ctx:
            chat_log.controls.append(bubble(t("chat_empty")))
            page.update()
            return
        pending = bubble(t("chat_thinking"))
        chat_log.controls.append(pending)
        page.update()

        def worker():
            answer = ask_ollama(cfg, question, ctx) if cfg.ollama_url else None

            def done():
                chat_log.controls.remove(pending)
                if answer:
                    chat_log.controls.append(bubble(answer))
                else:
                    chat_log.controls.append(bubble(t("chat_failed", model=cfg.ollama_model)))
                    chat_log.controls.extend(entry_card(e) for e in matched[:3])
                page.update()

            page.run_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    chat_in.on_submit = do_chat

    search_tab = ft.Column(expand=True, controls=[
        ft.Row([query, svg_button("search", t("search_hint"), do_search)]),
        mode_text,
        ft.Container(content=results, expand=2),
        ft.Divider(),
        ft.Container(content=chat_log, expand=3),
        ft.Row([chat_in, svg_button("send", t("tab_search"), do_chat)]),
    ])

    # ---------- 設定 ----------
    hotkey_handle = [None]

    def show_window():
        try:
            page.window.visible = True
            page.window.to_front()
        except Exception:
            pass
        page.update()

    def apply_hotkey():
        unregister_hotkey(hotkey_handle[0])
        hotkey_handle[0] = register_hotkey(cfg.hotkey, lambda: page.run_thread(show_window))

    def on_key(e: ft.KeyboardEvent):
        if e.key in ("Control", "Shift", "Alt", "Meta"):
            return
        parts = []
        if e.ctrl:
            parts.append("ctrl")
        if e.shift:
            parts.append("shift")
        if e.alt:
            parts.append("alt")
        if e.meta:
            parts.append("windows")
        parts.append(e.key.lower())
        s_hotkey.value = "+".join(parts)
        page.on_keyboard_event = None
        rec_btn.text = t("hotkey_record")
        page.update()

    def start_recording(_=None):
        page.on_keyboard_event = on_key
        rec_btn.text = t("hotkey_recording")
        page.update()

    def clear_hotkey(_=None):
        s_hotkey.value = ""
        page.update()

    def clear_all(_=None):
        store.clear()
        expanded.clear()
        refresh_timeline()
        snack(t("cleared"))

    def toggle_monitor(*_):
        cfg.monitoring = not cfg.monitoring
        cfg.save(cfg_path)

        def apply():
            s_monitor.value = cfg.monitoring
            snack(t("monitor_on") if cfg.monitoring else t("monitor_off"))

        page.run_thread(apply)

    def refresh_models(_=None):
        ollama_status.value = t("ollama_loading")
        page.update()
        url = s_ollama_url.value or cfg.ollama_url

        def worker():
            names = list_ollama_models(url)

            def done():
                if names is None:
                    ollama_status.value = t("ollama_failed")
                else:
                    current = ollama_dd.value or cfg.ollama_model
                    opts = list(dict.fromkeys(names + [current]))
                    ollama_dd.options = [ft.dropdown.Option(key=n, text=n) for n in opts]
                    ollama_dd.value = current
                    ollama_status.value = t("ollama_loaded", n=len(names))
                page.update()

            page.run_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    update_status = ft.Text(t("version_now", v=__version__))
    latest_url = [""]
    check_btn = ft.OutlinedButton(text=t("check_update"))
    open_btn = ft.OutlinedButton(text=t("open_download"), visible=False,
                                 on_click=lambda _: page.launch_url(latest_url[0]))

    def check_update(_=None):
        check_btn.disabled = True
        update_status.value = t("checking")
        page.update()

        def worker():
            info = check_latest()

            def done():
                check_btn.disabled = False
                if info is None:
                    update_status.value = t("update_failed")
                    open_btn.visible = False
                elif info["newer"]:
                    latest_url[0] = info["url"]
                    update_status.value = t("update_available", v=info["version"], cur=__version__)
                    open_btn.visible = True
                else:
                    update_status.value = t("up_to_date", cur=__version__)
                    open_btn.visible = False
                page.update()

            page.run_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    check_btn.on_click = check_update
    github_row = ft.Row(spacing=4, controls=[
        ft.Text(t("github_label"), size=12),
        ft.TextButton(text=REPO_URL, on_click=lambda _: page.launch_url(REPO_URL)),
    ])
    update_block = ft.Column(spacing=8, controls=[
        update_status,
        ft.Row([check_btn, open_btn]),
        github_row,
    ])

    def restart_app():
        if getattr(sys, "frozen", False):
            args = [sys.executable]
        else:
            args = [sys.executable, os.path.abspath(sys.argv[0])]
        flags = (0x00000008 | 0x00000200) if IS_WINDOWS else 0  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(args, creationflags=flags, close_fds=True,
                         env={**os.environ, "CTT_RESTART": "1"})
        except OSError:
            snack(t("restart_failed"))
            return
        quit_app()
        threading.Timer(2.0, lambda: os._exit(0)).start()

    restart_dlg = ft.AlertDialog(modal=True, title=ft.Text(t("restart_title")),
                                 content=ft.Text(t("restart_body")))

    def close_restart_dialog(_=None):
        restart_dlg.open = False
        page.update()

    def restart_now(_=None):
        close_restart_dialog()
        restart_app()

    def restart_later(_=None):
        close_restart_dialog()
        snack(t("lang_restart"))

    restart_dlg.actions = [
        ft.TextButton(text=t("restart_later"), on_click=restart_later),
        ft.ElevatedButton(text=t("restart_now"), on_click=restart_now),
    ]

    def show_restart_dialog():
        page.dialog = restart_dlg
        restart_dlg.open = True
        page.update()

    def save_settings(_=None):
        lang_changed = (s_lang.value or "en") != cfg.language
        cfg.monitoring = bool(s_monitor.value)
        cfg.retention_days = int(s_retention.value or 30)
        cfg.startup = bool(s_startup.value)
        cfg.hotkey = s_hotkey.value or ""
        cfg.ignored_apps = [x.strip() for x in (s_ignored.value or "").split(",") if x.strip()]
        cfg.semantic = bool(s_semantic.value)
        cfg.model_dir = s_model.value or ""
        cfg.ollama_url = s_ollama_url.value or ""
        cfg.ollama_model = ollama_dd.value or cfg.ollama_model
        cfg.language = s_lang.value or "en"
        cfg.close_to_tray = bool(s_tray.value)
        cfg.ollama_context_count = int(s_ctx_n.value or 15)
        cfg.save(cfg_path)
        if IS_WINDOWS:
            try:
                set_startup(cfg.startup)
            except OSError:
                snack(t("startup_failed"))
        apply_hotkey()
        store.purge(cfg.retention_days)
        refresh_timeline()
        if lang_changed:
            show_restart_dialog()
        else:
            snack(t("saved") + " " + t("semantic_note"))

    s_monitor = ft.Switch(label=t("set_monitoring"), value=cfg.monitoring)
    s_retention = ft.Dropdown(
        label=t("set_retention"), value=str(cfg.retention_days), width=200,
        options=[ft.dropdown.Option(key=str(d), text=t(RETENTION_KEYS[d])) for d in RETENTION_CHOICES],
    )
    s_lang = ft.Dropdown(
        label=t("set_language"), value=cfg.language, width=200,
        options=[ft.dropdown.Option(key="en", text="English"), ft.dropdown.Option(key="ja", text="日本語")],
    )
    s_startup = ft.Switch(label=t("set_startup"), value=cfg.startup, visible=IS_WINDOWS)
    s_tray = ft.Switch(label=t("set_close_tray"), value=cfg.close_to_tray, visible=IS_WINDOWS)
    s_hotkey = ft.TextField(label=t("set_hotkey"), value=cfg.hotkey, read_only=True,
                            hint_text=t("hotkey_unset"), width=260)
    rec_btn = ft.OutlinedButton(text=t("hotkey_record"), on_click=start_recording)
    s_ignored = ft.TextField(label=t("set_ignored"), value=", ".join(cfg.ignored_apps))
    s_semantic = ft.Switch(label=t("set_semantic"), value=cfg.semantic)
    s_model = ft.TextField(label=t("set_model_dir"), value=cfg.model_dir, hint_text=t("hint_model_dir"))
    semantic_status = ft.Text(
        t("semantic_loaded") if use_semantic() else t("semantic_not_loaded"),
        size=12, color=GREY)
    s_ollama_url = ft.TextField(label=t("set_ollama_url"), value=cfg.ollama_url)
    ollama_dd = ft.Dropdown(
        label=t("set_ollama_model"), width=320, value=cfg.ollama_model,
        options=[ft.dropdown.Option(key=cfg.ollama_model, text=cfg.ollama_model)],
    )
    ollama_status = ft.Text(size=12, color=GREY)
    s_ctx_n = ft.Dropdown(
        label=t("set_ctx_count"), width=200, value=str(cfg.ollama_context_count),
        options=[ft.dropdown.Option(key=str(n), text=str(n)) for n in (5, 10, 15, 20, 30, 50)],
    )
    ollama_refresh_btn = ft.OutlinedButton(text=t("ollama_refresh"), on_click=refresh_models)

    settings_tab = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
        s_monitor,
        s_retention,
        s_lang,
        s_startup,
        s_tray,
        ft.Row([s_hotkey, rec_btn, ft.TextButton(text=t("clear"), on_click=clear_hotkey)]),
        s_ignored,
        ft.Divider(),
        s_semantic,
        s_model,
        semantic_status,
        ft.Divider(),
        s_ollama_url,
        ft.Row([ollama_dd, ollama_refresh_btn]),
        ollama_status,
        s_ctx_n,
        ft.Divider(),
        update_block,
        ft.Divider(),
        ft.Row([
            ft.ElevatedButton(text=t("btn_save"), on_click=save_settings),
            ft.OutlinedButton(text=t("btn_clear_all"), on_click=clear_all),
        ]),
    ])

    # ---------- クリップボード監視（別スレッド） ----------
    def on_new():
        page.run_thread(refresh_timeline)

    monitor = ClipboardMonitor(cfg, store, embed, on_new)

    # ---------- システムトレイ（Windows）・ウィンドウ終了の扱い ----------
    tray = start_tray(
        title="Clipboard Time Travel",
        labels={"open": t("tray_open"), "monitor": t("tray_monitor"), "quit": t("tray_quit")},
        on_open=lambda: page.run_thread(show_window),
        on_toggle_monitor=lambda: toggle_monitor(),
        on_quit=lambda: quit_app(),
        is_monitoring=lambda: cfg.monitoring,
    ) if IS_WINDOWS else None

    quitting = [False]

    def quit_app(*_):
        quitting[0] = True
        monitor.stop()
        if tray is not None:
            tray.stop()

        def close():
            try:
                page.window.prevent_close = False
                page.window.close()
            except Exception:
                os._exit(0)

        page.run_thread(close)
        threading.Timer(3.0, lambda: os._exit(0)).start()  # 念のための終了保証

    def on_window_event(e):
        # Flet のバージョンによってイベントの形式が異なるため、両方を確認する
        is_close = getattr(e, "data", None) == "close" or str(getattr(e, "type", "")).lower().endswith("close")
        if not is_close or quitting[0]:
            return
        if cfg.close_to_tray and tray is not None:
            page.window.visible = False
            page.update()
        else:
            quit_app()

    # ---------- 組み立て ----------
    page.add(ft.Tabs(expand=True, selected_index=0, tabs=[
        ft.Tab(text=t("tab_timeline"), content=timeline),
        ft.Tab(text=t("tab_search"), content=search_tab),
        ft.Tab(text=t("tab_settings"), content=settings_tab),
    ]))
    if tray is not None:
        page.window.prevent_close = True
        page.window.on_event = on_window_event
    refresh_timeline()
    apply_hotkey()
    monitor.start()
    refresh_models()


if __name__ == "__main__":
    # 再起動直後は前のプロセスが終わるまで待つ。それ以外で既に起動していれば前面に出して終了する
    restarting = os.environ.get("CTT_RESTART") == "1"
    if not acquire_instance(data_dir(), wait_seconds=10 if restarting else 0):
        activate_existing_window()
        sys.exit(0)
    ft.app(target=main, assets_dir="assets")
