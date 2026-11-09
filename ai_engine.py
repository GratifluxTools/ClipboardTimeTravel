"""検索とチャット。
- 既定: 軽量なキーワード検索（追加ダウンロードなし）
- 任意: ONNX の多言語MiniLMで意味検索（numpy/onnxruntime/tokenizers とモデルフォルダが必要）
- 任意: ローカルの Ollama でチャット（有料APIは使わない）。接続できなければ None を返す。
"""
import json
import os
import re
import urllib.error
import urllib.request

from storage import fmt_time


class Embedder:
    def __init__(self, model_dir: str):
        self.ok = False
        self.np = None
        try:
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer

            self.np = np
            self._tok = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
            self._tok.enable_truncation(max_length=256)
            self._sess = ort.InferenceSession(os.path.join(model_dir, "model.onnx"),
                                              providers=["CPUExecutionProvider"])
            self._names = {i.name for i in self._sess.get_inputs()}
            self.ok = True
        except Exception:
            self.ok = False

    def encode(self, text: str):
        if not self.ok:
            return None
        np = self.np
        enc = self._tok.encode(text)
        ids = np.array([enc.ids], dtype=np.int64)
        mask = np.array([enc.attention_mask], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self._sess.run(None, feeds)[0]
        m = mask[..., None].astype(np.float32)
        vec = (hidden * m).sum(axis=1)[0] / max(float(m.sum()), 1e-9)  # mean pooling
        vec = vec / max(float(np.linalg.norm(vec)), 1e-9)
        return vec.astype(np.float32).tobytes()


def semantic_search(embedder, store, query: str, k: int = 5):
    qb = embedder.encode(query)
    if qb is None:
        return []
    np = embedder.np
    q = np.frombuffer(qb, dtype=np.float32)
    scored = []
    for entry, eb in store.with_embeddings():
        v = np.frombuffer(eb, dtype=np.float32)
        if v.shape == q.shape:
            scored.append((float(q @ v), entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:k]]


_SPLIT = re.compile(r"[\s、。,.!?！？「」]+")


def _terms(q: str) -> set:
    terms = set()
    for part in _SPLIT.split(q.lower()):
        if not part:
            continue
        terms.add(part)
        if len(part) > 2:  # 日本語は空白で区切られないので2文字ずつも使う
            terms.update(part[i:i + 2] for i in range(len(part) - 1))
    return terms


def keyword_search(store, query: str, k: int = 20):
    terms = _terms(query)
    if not terms:
        return []
    scored = []
    for e in store.recent(5000):
        hay = (e["text"] + " " + e["window"] + " " + e["app"]).lower()
        s = sum(1 for t in terms if t in hay)
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], -x[1]["id"]))
    return [e for _, e in scored[:k]]


def ask_ollama(cfg, question: str, context) -> str | None:
    lines = []
    for i, e in enumerate(context, 1):
        lines.append(f"[{i}] {fmt_time(e['time'])} / {e['app']} / {e['window']}\n{e['text'][:800]}")
    prompt = (
        "あなたは利用者のクリップボード履歴を参照して答えるアシスタントです。"
        "以下の履歴だけを根拠に、日本語で簡潔に答えてください。根拠がなければその旨を伝えてください。\n\n"
        "履歴:\n" + "\n\n".join(lines) + f"\n\n質問: {question}\n回答:"
    )
    body = json.dumps({"model": cfg.ollama_model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(cfg.ollama_url.rstrip("/") + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = json.loads(resp.read().decode("utf-8")).get("response", "").strip()
            return text or None
    except (urllib.error.URLError, OSError, ValueError):
        return None
