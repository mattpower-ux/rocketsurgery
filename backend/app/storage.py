import json
import re
from pathlib import Path

BASE_DIR = Path("/data/rocketsurgery")
WALKTHROUGHS_DIR = BASE_DIR / "walkthroughs"
IMAGES_DIR = BASE_DIR / "images"


def ensure_storage():
    WALKTHROUGHS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def query_to_walkthrough_id(query: str) -> str:
    q = query.lower()

    if "james hardie" in q or "hardie" in q:
        if "siding" in q or "lap" in q or "nailing" in q:
            return "james-hardie-lap-siding-nailing-schedule"

    synonym_map = {
        "footers": "footings",
        "footer": "footing",
        "sonotube": "form tube",
        "sonotubes": "form tubes",
        "post holes": "footings",
        "deck post": "post",
        "fence post": "post"
    }

    filler_words = [
        "how to",
        "install",
        "replace",
        "build",
        "repair",
        "fix",
        "tutorial",
        "guide",
        "diy"
    ]

    for old_word, new_word in synonym_map.items():
        q = q.replace(old_word, new_word)

    for filler in filler_words:
        q = q.replace(filler, "")

    q = re.sub(r"\s+", " ", q).strip()

    return slugify(q)


def walkthrough_path(walkthrough_id: str) -> Path:
    return WALKTHROUGHS_DIR / walkthrough_id / "manifest.json"


def image_path(filename: str) -> Path:
    ensure_storage()
    return IMAGES_DIR / filename


def load_walkthrough(query: str):
    ensure_storage()

    walkthrough_id = query_to_walkthrough_id(query)
    path = walkthrough_path(walkthrough_id)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_walkthrough(walkthrough_id: str, manifest: dict):
    ensure_storage()

    folder = WALKTHROUGHS_DIR / walkthrough_id
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / "manifest.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return path
