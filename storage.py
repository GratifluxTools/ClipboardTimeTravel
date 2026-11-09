import json
import sqlite3
import threading
import time
from datetime import datetime


def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


class HistoryStore:
    """履歴は本文・コピー元などをすべて暗号化して保存する。時刻だけは保存期間の管理用に平文。"""

    def __init__(self, db_path: str, vault):
        self._vault = vault
        self._lock = threading.Lock()
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                payload BLOB NOT NULL,
                emb BLOB
            );
            CREATE INDEX IF NOT EXISTS idx_created ON entries(created_at);
        """)
        self._db.commit()

    def add(self, text, app="", window="", emb=None) -> int:
        payload = self._vault.encrypt(
            json.dumps({"t": text, "a": app, "w": window}, ensure_ascii=False).encode("utf-8"))
        enc_emb = self._vault.encrypt(emb) if emb else None
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO entries(created_at, payload, emb) VALUES (?,?,?)",
                (int(time.time()), payload, enc_emb))
            self._db.commit()
            return cur.lastrowid

    def _decode(self, row):
        rid, ts, payload = row[0], row[1], row[2]
        d = json.loads(self._vault.decrypt(payload).decode("utf-8"))
        return {"id": rid, "time": ts, "text": d["t"], "app": d["a"], "window": d["w"]}

    def recent(self, limit=300):
        with self._lock:
            rows = self._db.execute(
                "SELECT id, created_at, payload FROM entries ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [self._decode(r) for r in rows]

    def with_embeddings(self, limit=5000):
        with self._lock:
            rows = self._db.execute(
                "SELECT id, created_at, payload, emb FROM entries WHERE emb IS NOT NULL "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [(self._decode(r), self._vault.decrypt(r[3])) for r in rows]

    def delete(self, rid: int) -> None:
        with self._lock:
            self._db.execute("DELETE FROM entries WHERE id=?", (rid,))
            self._db.commit()

    def purge(self, days: int) -> None:
        if days <= 0:
            return
        cutoff = int(time.time()) - days * 86400
        with self._lock:
            cur = self._db.execute("DELETE FROM entries WHERE created_at < ?", (cutoff,))
            self._db.commit()
            if cur.rowcount:
                self._db.execute("VACUUM")  # ファイルサイズを縮める

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM entries")
            self._db.commit()
            self._db.execute("VACUUM")
