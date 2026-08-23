import json
import re
import time
from pathlib import Path

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR

try:
    from app.metadata_repository import metadata_repository
except ImportError:
    from metadata_repository import metadata_repository


INDEX_PATH = BASE_DIR / "walkthrough-index.json"


def normalize_search_text(text: str) -> str:
    normalized = (text or "").lower().strip()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\b(how|to|the|a|an|diy|guide|tutorial)\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def infer_category_from_manifest(manifest: dict) -> str:
    blob = " ".join([
        manifest.get("category", ""),
        manifest.get("walkthrough_id", ""),
        manifest.get("title", ""),
        manifest.get("query", ""),
    ]).lower()

    category_terms = [
        ("toilet", ["toilet", "commode", "water closet"]),
        ("faucet", ["faucet", "sink fixture"]),
        ("dishwasher", ["dishwasher"]),
        ("electrical", ["outlet", "gfci", "switch", "panel", "wiring"]),
        ("hvac", ["hvac", "heat pump", "thermostat", "air handler"]),
        ("water_heater", ["water heater", "tankless"]),
        ("flooring", ["floor", "flooring", "tile", "hardwood"]),
        ("roofing", ["roof", "shingle", "flashing"]),
        ("siding", ["siding", "hardie", "fiber cement"]),
        ("door_window", ["door", "window", "sash"]),
    ]

    for category, terms in category_terms:
        if any(term in blob for term in terms):
            return category

    return "generic"


def load_index() -> dict:
    if not INDEX_PATH.exists():
        return {"schema_version": 1, "updated_at": "", "walkthroughs": {}}

    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("schema_version", 1)
    data.setdefault("updated_at", "")
    data.setdefault("walkthroughs", {})
    return data


def save_index(index: dict) -> dict:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def build_aliases(manifest: dict) -> list[str]:
    aliases = set()
    for value in [
        manifest.get("query", ""),
        manifest.get("title", ""),
        manifest.get("walkthrough_id", ""),
    ]:
        normalized = normalize_search_text(value)
        if normalized:
            aliases.add(normalized)

    for value in manifest.get("aliases", []) or []:
        normalized = normalize_search_text(value)
        if normalized:
            aliases.add(normalized)

    return sorted(aliases)


def build_index_record(walkthrough_id: str, manifest: dict, manifest_path: Path | None = None) -> dict:
    steps = manifest.get("steps", []) or []
    image_urls = [
        step.get("imageUrl", "")
        for step in steps
        if step.get("imageUrl")
    ]

    return {
        "walkthrough_id": walkthrough_id,
        "canonical_query": manifest.get("query", manifest.get("title", walkthrough_id)),
        "title": manifest.get("title", walkthrough_id),
        "walkthrough_type": manifest.get("walkthrough_type", "generic_foundation"),
        "aliases": build_aliases(manifest),
        "category": infer_category_from_manifest(manifest),
        "review_status": manifest.get("review_status", "draft"),
        "quality_status": manifest.get("quality_status", "unvalidated"),
        "version": manifest.get("version", 1),
        "step_count": len(steps),
        "image_count": len(image_urls),
        "image_urls": image_urls,
        "manifest_path": str(manifest_path) if manifest_path else "",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def update_walkthrough_index(walkthrough_id: str, manifest: dict, manifest_path: Path | None = None) -> dict:
    index = load_index()
    record = build_index_record(walkthrough_id, manifest, manifest_path)
    index["walkthroughs"][walkthrough_id] = record
    metadata_repository.upsert_record("walkthroughs", walkthrough_id, record)
    return save_index(index)


def remove_walkthrough_from_index(walkthrough_id: str) -> dict:
    index = load_index()
    index.get("walkthroughs", {}).pop(walkthrough_id, None)
    return save_index(index)


def find_walkthrough_id_for_query(query: str) -> str:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return ""

    index = load_index()
    records = index.get("walkthroughs", {})

    for walkthrough_id, record in records.items():
        aliases = record.get("aliases", []) or []
        if normalized_query in aliases:
            return walkthrough_id

    query_terms = set(normalized_query.split())
    if len(query_terms) < 2:
        return ""

    best_id = ""
    best_score = 0

    for walkthrough_id, record in records.items():
        aliases = record.get("aliases", []) or []
        for alias in aliases:
            alias_terms = set(alias.split())
            if not alias_terms:
                continue
            overlap = len(query_terms & alias_terms)
            score = overlap / max(len(query_terms), len(alias_terms))
            if score > best_score:
                best_id = walkthrough_id
                best_score = score

    return best_id if best_score >= 0.72 else ""
