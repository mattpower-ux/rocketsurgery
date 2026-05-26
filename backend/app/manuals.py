import json
from pathlib import Path

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


MANUALS_DIR = BASE_DIR / "manuals"
MANUAL_INDEX_FILE = MANUALS_DIR / "manual-index.json"


def ensure_manual_storage():
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)

    if not MANUAL_INDEX_FILE.exists():
        with MANUAL_INDEX_FILE.open("w", encoding="utf-8") as f:
            json.dump({"manuals": []}, f, indent=2)


def load_manual_index():
    ensure_manual_storage()

    with MANUAL_INDEX_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_manual_index(index: dict):
    ensure_manual_storage()

    with MANUAL_INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    return index


def manual_storage_status():
    ensure_manual_storage()
    index = load_manual_index()

    return {
        "status": "manual storage ready",
        "manuals_dir": str(MANUALS_DIR),
        "manual_index_file": str(MANUAL_INDEX_FILE),
        "manual_count": len(index.get("manuals", []))
    }
