import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "episodes.json"
CONFIG_FILE = ROOT / "site.config.json"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_episodes():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_episodes(episodes):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(episodes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text, max_len=80):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rsplit("-", 1)[0]
    return text or "episodio"
