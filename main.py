import os
import sys
import threading

import flet as ft

from ai_engine import Embedder, ask_ollama, keyword_search, semantic_search
from config import RETENTION_CHOICES, Config, data_dir
from crypto_utils import Vault
from monitor import ClipboardMonitor, register_hotkey, unregister_hotkey
from startup import set_startup
from storage import HistoryStore, fmt_time
from app_version import __version__
from updater import check_latest

IS_WINDOWS = sys.platform == "win32"
RETENTION_LABEL = {1: "1日", 7: "7日", 30: "30日", 90: "90日", 365: "1年", 0: "無期限"}


def svg_button(name, tooltip, on_click):
    return ft.IconButton(
        content=ft.Image(src=f"icons/{name}.svg", width=20, height=20),
        tooltip=tooltip,
        on_click=on_click,
    )


def main(page: ft.Page):
    page.title = "Clipboard Time Travel"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 12

    ddir = data_dir()
    cfg_path = os.path.join(ddir, "config.json")
    cfg = Config.load(cfg_path)
    try:
        vault = Vault(os.path.join(ddir, "key.bin"))
    except Exception as ex:
        page.add(ft.Text(f"暗号化キーを読み込めませんでした: {ex}", color=ft.Colors.RED))
        return
    store = HistoryStore(os.path.join(ddir, "history.db"), vault)
    store.purge(cfg.retention_days)

    embedder = Embedder(cfg.model_dir) if (cfg.semantic and cfg.model_dir) else None

    def use_semantic():
        return embedder is not None and embedder.ok

    def embed(text):
        return embedder.encode(text) if use_semantic() else None

    def snack(msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    # ---------- 共通のカード ----------
    def copy_entry(e):
        monitor.mark(e["text"])
        page.set_clipboard(e["text"])
        snack("コピーしました")

    def delete_entry(rid):
        store.delete(rid)
        refresh_timeline()

    def entry_card(e):
        body = e["text"] if len(e["text"]) <= 300 else e["text"][:300] + "…"
        return ft.Card(content=ft.Container(padding=10, content=ft.Column(spacing=4, controls=[
            ft.Row([
                ft.Text(fmt_time(e["time"]), size=12, color=ft.Colors.GREY),
                ft.Text(e["app"] or "不明", size=12, weight=ft.FontWeight.BOLD, expand=True,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ]),
            ft.Text(e["window"], size=11, color=ft.Colors.GREY, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(body, selectable=True),
            ft.Row([
                svg_button("copy", "コピー", lambda _, x=e: copy_entry(x)),
                svg_button("trash", "削除", lambda _, rid=e["id"]: delete_entry(rid)),
            ], alignment=ft.MainAxisAlignment.END),
        ])))

    # ---------- タイムライン ----------
    timeline = ft.ListView(expand=True, spacing=8)

    def refresh_timeline():
        items = store.recent(300)
        timeline.controls = [entry_card(e) for e in items] or [ft.Text("まだ履歴がありません")]
        page.update()

    # ---------- 検索・チャット ----------
    def find(q, k):
        if use_semantic():
            return semantic_search(embedder, store, q, k), "意味検索"
        return keyword_search(store, q, k), "キーワード検索"

    query = ft.TextField(hint_text="例：先週の住所", expand=True)
    mode_text = ft.Text(size=12, color=ft.Colors.GREY)
    results = ft.ListView(expand=True, spacing=8)

    def do_search(_=None):
        q = (query.value or "").strip()
        if not q:
            return
        items, mode = find(q, 5 if use_semantic() else 20)
        mode_text.value = f"{mode}: {len(items)}件"
        results.controls = [entry_card(e) for e in items] or [ft.Text("一致する履歴がありません")]
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
    chat_in = ft.TextField(hint_text="履歴について質問（例：◯◯のメモはあったっけ？）", expand=True)

    def chat_context(question):
        matched, _mode = find(question, 8)
        seen = {e["id"] for e in matched}
        recent = [e for e in store.recent(20) if e["id"] not in seen]
        return matched, (matched + recent)[:15]

    def do_chat(_=None):
        question = (chat_in.value or "").strip()
        if not question:
            return
        chat_in.value = ""
        chat_log.controls.append(bubble(question, mine=True))
        matched, ctx = chat_context(question)
        if not ctx:
            chat_log.controls.append(bubble("まだ履歴がないため、回答できません。"))
            page.update()
            return
        pending = bubble("考え中…")
        chat_log.controls.append(pending)
        page.update()

        def worker():
            answer = ask_ollama(cfg, question, ctx) if cfg.ollama_url else None

            def done():
                chat_log.controls.remove(pending)
                if answer:
                    chat_log.controls.append(bubble(answer))
                else:
                    chat_log.controls.append(bubble(
                        "AIから回答を取得できませんでした。Ollamaが起動しているか、"
                        f"モデル「{cfg.ollama_model}」を取得済みか確認してください（設定画面で変更可）。"))
                    chat_log.controls.extend(entry_card(e) for e in matched[:3])
                page.update()

            page.run_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    chat_in.on_submit = do_chat

    search_tab = ft.Column(expand=True, controls=[
        ft.Row([query, svg_button("search", "検索", do_search)]),
        mode_text,
        ft.Container(content=results, expand=2),
        ft.Divider(),
        ft.Container(content=chat_log, expand=3),
        ft.Row([chat_in, svg_button("send", "送信", do_chat)]),
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
        rec_btn.text = "キー入力で設定"
        page.update()

    def start_recording(_=None):
        page.on_keyboard_event = on_key
        rec_btn.text = "キーを押してください…"
        page.update()

    def clear_hotkey(_=None):
        s_hotkey.value = ""
        page.update()

    def clear_all(_=None):
        store.clear()
        refresh_timeline()
        snack("全履歴を削除しました")

    def save_settings(_=None):
        cfg.monitoring = bool(s_monitor.value)
        cfg.retention_days = int(s_retention.value or 30)
        cfg.startup = bool(s_startup.value)
        cfg.hotkey = s_hotkey.value or ""
        cfg.ignored_apps = [x.strip() for x in (s_ignored.value or "").split(",") if x.strip()]
        cfg.semantic = bool(s_semantic.value)
        cfg.model_dir = s_model.value or ""
        cfg.ollama_url = s_ollama_url.value or ""
        cfg.ollama_model = s_ollama_model.value or ""
        cfg.save(cfg_path)
        if IS_WINDOWS:
            try:
                set_startup(cfg.startup)
            except OSError:
                snack("スタートアップ登録に失敗しました")
        apply_hotkey()
        store.purge(cfg.retention_days)
        refresh_timeline()
        snack("保存しました（意味検索の変更は再起動後に反映）")

    s_monitor = ft.Switch(label="クリップボード監視", value=cfg.monitoring)
    s_retention = ft.Dropdown(
        label="保存期間", value=str(cfg.retention_days), width=200,
        options=[ft.dropdown.Option(key=str(d), text=RETENTION_LABEL[d]) for d in RETENTION_CHOICES],
    )
    s_startup = ft.Switch(label="Windows起動時に自動実行", value=cfg.startup, visible=IS_WINDOWS)
    s_hotkey = ft.TextField(label="ショートカットキー", value=cfg.hotkey, read_only=True,
                            hint_text="未設定", width=260)
    rec_btn = ft.OutlinedButton(text="キー入力で設定", on_click=start_recording)
    s_ignored = ft.TextField(label="除外するアプリ（カンマ区切り・部分一致）",
                             value=", ".join(cfg.ignored_apps))
    s_semantic = ft.Switch(label="意味検索を使う（要モデル配置）", value=cfg.semantic)
    s_model = ft.TextField(label="モデルフォルダ", value=cfg.model_dir,
                           hint_text="tokenizer.json と model.onnx を置いたフォルダ")
    semantic_status = ft.Text(
        "読み込み済み" if use_semantic() else "未読み込み（キーワード検索で動作）",
        size=12, color=ft.Colors.GREY)
    s_ollama_url = ft.TextField(label="Ollama URL（任意・ローカルのみ）", value=cfg.ollama_url)
    s_ollama_model = ft.TextField(label="Ollamaモデル名", value=cfg.ollama_model)

    update_status = ft.Text(f"現在のバージョン: {__version__}")
    latest_url = [""]
    check_btn = ft.OutlinedButton(text="更新を確認")
    open_btn = ft.OutlinedButton(text="ダウンロードページを開く", visible=False,
                                 on_click=lambda _: page.launch_url(latest_url[0]))

    def check_update(_=None):
        check_btn.disabled = True
        update_status.value = "確認中…"
        page.update()

        def worker():
            info = check_latest()

            def done():
                check_btn.disabled = False
                if info is None:
                    update_status.value = "更新情報を取得できませんでした。ネットワーク接続を確認してください。"
                    open_btn.visible = False
                elif info["newer"]:
                    latest_url[0] = info["url"]
                    update_status.value = f"新しいバージョン {info['version']} があります（現在 {__version__}）"
                    open_btn.visible = True
                else:
                    update_status.value = f"最新バージョンです（{__version__}）"
                    open_btn.visible = False
                page.update()

            page.run_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    check_btn.on_click = check_update
    update_block = ft.Column(spacing=8, controls=[update_status, ft.Row([check_btn, open_btn])])

    settings_tab = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
        s_monitor,
        s_retention,
        s_startup,
        ft.Row([s_hotkey, rec_btn, ft.TextButton(text="クリア", on_click=clear_hotkey)]),
        s_ignored,
        ft.Divider(),
        s_semantic,
        s_model,
        semantic_status,
        ft.Divider(),
        s_ollama_url,
        s_ollama_model,
        ft.Divider(),
        update_block,
        ft.Divider(),
        ft.Row([
            ft.ElevatedButton(text="設定を保存", on_click=save_settings),
            ft.OutlinedButton(text="全履歴を削除", on_click=clear_all),
        ]),
    ])

    # ---------- クリップボード監視（別スレッド） ----------
    def on_new():
        page.run_thread(refresh_timeline)

    monitor = ClipboardMonitor(cfg, store, embed, on_new)

    # ---------- 組み立て ----------
    page.add(ft.Tabs(expand=True, selected_index=0, tabs=[
        ft.Tab(text="タイムライン", content=timeline),
        ft.Tab(text="検索・チャット", content=search_tab),
        ft.Tab(text="設定", content=settings_tab),
    ]))
    refresh_timeline()
    apply_hotkey()
    monitor.start()


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
