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


def normalize_query_text(query: str) -> str:
    q = (query or "").lower().strip()

    synonym_map = {
        "footers": "footings",
        "footer": "footing",
        "sonotubes": "form tubes",
        "sonotube": "form tube",
        "post holes": "footings",
        "post hole": "footing",
        "deck post": "post",
        "deck posts": "posts",
        "fence post": "post",
        "fence posts": "posts"
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
        "diy",
        "the",
        "a",
        "an"
    ]

    for old_word, new_word in synonym_map.items():
        q = q.replace(old_word, new_word)

    for filler in filler_words:
        q = re.sub(rf"\b{re.escape(filler)}\b", " ", q)

    q = re.sub(r"\s+", " ", q).strip()

    return q


def query_to_walkthrough_id(query: str) -> str:
    q = normalize_query_text(query)

    if "james hardie" in q or "hardie" in q:
        if "siding" in q or "lap" in q or "nailing" in q:
            return "james-hardie-lap-siding-nailing-schedule"

    # Canonical construction task aliases.
    # Keep high-frequency tasks mapped to one reusable cache key.
    if (
        "post" in q and
        ("footing" in q or "footings" in q) and
        (
            "concrete" in q or
            "pour" in q or
            "deck" in q or
            "fence" in q or
            "form tube" in q or
            "form tubes" in q
        )
    ):
        return "concrete-post-footings"

    if (
        "concrete" in q and
        "slab" in q
    ):
        return "pour-concrete-slab"

    if (
        "load bearing" in q and
        "wall" in q
    ):
        return "find-load-bearing-wall"

    if (
        "non load bearing" in q and
        "wall" in q
    ):
        return "remove-non-load-bearing-wall"

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


def load_walkthrough_by_id(walkthrough_id: str):
    """Load a walkthrough manifest directly by its stored walkthrough_id."""
    ensure_storage()
    safe_id = slugify(walkthrough_id or "")
    path = walkthrough_path(safe_id)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_walkthrough_manifests(limit: int = 250):
    """Return a lightweight list of saved walkthrough manifests."""
    ensure_storage()
    items = []

    for manifest_path in WALKTHROUGHS_DIR.glob("*/manifest.json"):
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)

            stat = manifest_path.stat()
            steps = manifest.get("steps", []) or []

            items.append({
                "walkthrough_id": manifest.get("walkthrough_id") or manifest_path.parent.name,
                "title": manifest.get("title", manifest_path.parent.name),
                "step_count": len(steps),
                "modified_at": stat.st_mtime,
                "modified_at_iso": __import__("datetime").datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=__import__("datetime").timezone.utc
                ).isoformat(),
                "first_image_url": steps[0].get("imageUrl") if steps else ""
            })
        except Exception as e:
            items.append({
                "walkthrough_id": manifest_path.parent.name,
                "title": manifest_path.parent.name,
                "step_count": 0,
                "modified_at": 0,
                "modified_at_iso": "",
                "first_image_url": "",
                "error": str(e)
            })

    items.sort(key=lambda item: item.get("modified_at", 0), reverse=True)
    return items[:limit]
