import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields

DEFAULT_IGNORED = ["keepass", "1password", "bitwarden", "lastpass", "dashlane", "keeper"]
RETENTION_CHOICES = [1, 7, 30, 90, 365, 0]  # 0 = 無期限


def data_dir() -> str:
    base = os.environ.get("FLET_APP_STORAGE_DATA")  # Flet が設定する場合はその場所を使う
    if not base:
        if sys.platform == "win32":
            base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ClipboardTimeTravel")
        else:
            base = os.path.join(os.path.expanduser("~"), ".clipboard_time_travel")
    os.makedirs(base, exist_ok=True)
    return base


@dataclass
class Config:
    monitoring: bool = True
    retention_days: int = 30
    hotkey: str = ""
    startup: bool = False
    ignored_apps: list = field(default_factory=lambda: list(DEFAULT_IGNORED))
    semantic: bool = False
    model_dir: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    @classmethod
    def load(cls, path: str) -> "Config":
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return cls()
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, ensure_ascii=False, indent=2)
