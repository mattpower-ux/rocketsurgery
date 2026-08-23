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
WALKTHROUGHS_DIR = BASE_DIR / "walkthroughs"
TAXONOMY_PATH = Path(__file__).with_name("search_phrase_taxonomy.json")
TAXONOMY_COVERAGE_PATH = BASE_DIR / "walkthrough-taxonomy-coverage.json"


def normalize_search_text(text: str) -> str:
    normalized = (text or "").lower().strip()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"\b(mouse|mouses)\b", "mice", normalized)
    normalized = re.sub(
        r"\b(getting rid of|get rid of|remove|removing|kill|killing|exterminate|exterminating)\b",
        " rid ",
        normalized
    )
    normalized = re.sub(r"\bget\s+(?:a\s+)?mice\s+out\b", " rid mice ", normalized)
    normalized = re.sub(r"\b(fix|repair|stop|stopping|seal|sealing)\b", " repair ", normalized)
    normalized = re.sub(r"\b(leaky|leaking|leaks)\b", " leak ", normalized)
    normalized = re.sub(r"\bfaucet\s+leak\b", " leak faucet ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\b(how|to|the|a|an|diy|guide|tutorial|my|your|from|of|in|out)\b", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def alias_similarity(source: str, target: str) -> float:
    source_terms = set(source.split())
    target_terms = set(target.split())
    if not source_terms or not target_terms:
        return 0

    if source_terms == target_terms:
        return 1

    if len(source_terms) >= 2 and source_terms.issubset(target_terms):
        return 0.92

    if len(target_terms) >= 2 and target_terms.issubset(source_terms):
        return 0.92

    overlap = len(source_terms & target_terms)
    return overlap / max(len(source_terms), len(target_terms))


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


def load_search_phrase_taxonomy() -> dict:
    if not TAXONOMY_PATH.exists():
        return {"schema_version": 1, "walkthroughs": {}}

    try:
        data = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("schema_version", 1)
    data.setdefault("walkthroughs", {})
    return data


def load_taxonomy_coverage() -> dict:
    if not TAXONOMY_COVERAGE_PATH.exists():
        return {
            "schema_version": 1,
            "summary": {},
            "taxonomy_coverage": {},
            "unmatched_existing_walkthroughs": [],
            "errors": [],
        }

    try:
        data = json.loads(TAXONOMY_COVERAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("summary", {})
    data.setdefault("taxonomy_coverage", {})
    data.setdefault("unmatched_existing_walkthroughs", [])
    data.setdefault("errors", [])
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


def taxonomy_aliases(entry: dict) -> list[str]:
    aliases = set()
    for value in [
        entry.get("walkthrough_id", ""),
        entry.get("canonical_query", ""),
        entry.get("title", ""),
        *(entry.get("aliases", []) or []),
    ]:
        normalized = normalize_search_text(value)
        if normalized:
            aliases.add(normalized)
    return sorted(aliases)


def match_score(source_aliases: set[str], target_aliases: set[str]) -> float:
    if not source_aliases or not target_aliases:
        return 0

    if source_aliases & target_aliases:
        return 1

    best_score = 0
    for source in source_aliases:
        source_terms = set(source.split())
        if len(source_terms) < 2:
            continue
        for target in target_aliases:
            target_terms = set(target.split())
            if len(target_terms) < 2:
                continue
            score = alias_similarity(source, target)
            best_score = max(best_score, score)

    return best_score


def find_taxonomy_match_for_manifest(manifest: dict, walkthrough_id: str) -> dict:
    taxonomy = load_search_phrase_taxonomy()
    manifest_aliases = set(build_aliases({
        **manifest,
        "walkthrough_id": walkthrough_id,
    }))
    best_entry = None
    best_aliases = []
    best_score = 0

    for taxonomy_id, entry in taxonomy.get("walkthroughs", {}).items():
        aliases = taxonomy_aliases({
            **entry,
            "walkthrough_id": entry.get("walkthrough_id") or taxonomy_id,
        })
        score = match_score(manifest_aliases, set(aliases))
        if score > best_score:
            best_entry = {
                **entry,
                "walkthrough_id": entry.get("walkthrough_id") or taxonomy_id,
            }
            best_aliases = aliases
            best_score = score

    if not best_entry or best_score < 0.72:
        return {}

    return {
        "taxonomy_walkthrough_id": best_entry.get("walkthrough_id", ""),
        "taxonomy_canonical_query": best_entry.get("canonical_query", ""),
        "taxonomy_title": best_entry.get("title", ""),
        "taxonomy_category": best_entry.get("category", ""),
        "taxonomy_match_score": round(best_score, 3),
        "taxonomy_aliases": best_aliases,
    }


def build_index_record(walkthrough_id: str, manifest: dict, manifest_path: Path | None = None) -> dict:
    steps = manifest.get("steps", []) or []
    image_urls = [
        step.get("imageUrl", "")
        for step in steps
        if step.get("imageUrl")
    ]

    aliases = set(build_aliases(manifest))
    taxonomy_match = find_taxonomy_match_for_manifest(manifest, walkthrough_id)
    aliases.update(taxonomy_match.get("taxonomy_aliases", []) or [])

    return {
        "walkthrough_id": walkthrough_id,
        "storage_walkthrough_id": walkthrough_id,
        "manifest_walkthrough_id": manifest.get("walkthrough_id", walkthrough_id),
        "canonical_query": manifest.get("query", manifest.get("title", walkthrough_id)),
        "title": manifest.get("title", walkthrough_id),
        "walkthrough_type": manifest.get("walkthrough_type", "generic_foundation"),
        "aliases": sorted(aliases),
        "category": infer_category_from_manifest(manifest),
        "taxonomy_walkthrough_id": taxonomy_match.get("taxonomy_walkthrough_id", ""),
        "taxonomy_canonical_query": taxonomy_match.get("taxonomy_canonical_query", ""),
        "taxonomy_title": taxonomy_match.get("taxonomy_title", ""),
        "taxonomy_category": taxonomy_match.get("taxonomy_category", ""),
        "taxonomy_match_score": taxonomy_match.get("taxonomy_match_score", 0),
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


def rebuild_walkthrough_index_from_storage() -> dict:
    WALKTHROUGHS_DIR.mkdir(parents=True, exist_ok=True)
    taxonomy = load_search_phrase_taxonomy()
    taxonomy_coverage = {
        taxonomy_id: {
            "taxonomy_walkthrough_id": entry.get("walkthrough_id") or taxonomy_id,
            "canonical_query": entry.get("canonical_query", ""),
            "title": entry.get("title", ""),
            "category": entry.get("category", ""),
            "coverage_status": "prospective_only",
            "existing_walkthrough_ids": [],
        }
        for taxonomy_id, entry in taxonomy.get("walkthroughs", {}).items()
    }
    records = {}
    errors = []
    unmatched_existing = []

    for manifest_path in sorted(WALKTHROUGHS_DIR.glob("*/manifest.json")):
        walkthrough_id = manifest_path.parent.name
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = build_index_record(walkthrough_id, manifest, manifest_path)
            records[walkthrough_id] = record
            metadata_repository.upsert_record("walkthroughs", walkthrough_id, record)

            taxonomy_id = record.get("taxonomy_walkthrough_id", "")
            if taxonomy_id and taxonomy_id in taxonomy_coverage:
                taxonomy_coverage[taxonomy_id]["coverage_status"] = "existing_walkthrough_available"
                taxonomy_coverage[taxonomy_id]["existing_walkthrough_ids"].append(walkthrough_id)
            else:
                unmatched_existing.append({
                    "walkthrough_id": walkthrough_id,
                    "title": record.get("title", ""),
                    "canonical_query": record.get("canonical_query", ""),
                    "category": record.get("category", ""),
                    "review_status": record.get("review_status", ""),
                    "quality_status": record.get("quality_status", ""),
                })
        except Exception as exc:
            errors.append({
                "walkthrough_id": walkthrough_id,
                "manifest_path": str(manifest_path),
                "error": str(exc),
            })

    index = {
        "schema_version": 1,
        "source": "storage_scan",
        "walkthroughs": records,
    }
    save_index(index)

    covered_count = len([
        item for item in taxonomy_coverage.values()
        if item.get("coverage_status") == "existing_walkthrough_available"
    ])
    coverage = {
        "schema_version": 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "stored_walkthrough_count": len(records),
            "taxonomy_entry_count": len(taxonomy_coverage),
            "taxonomy_entries_with_existing_walkthroughs": covered_count,
            "prospective_taxonomy_entries_without_existing_walkthroughs": len(taxonomy_coverage) - covered_count,
            "unmatched_existing_walkthrough_count": len(unmatched_existing),
            "error_count": len(errors),
        },
        "taxonomy_coverage": taxonomy_coverage,
        "unmatched_existing_walkthroughs": unmatched_existing,
        "errors": errors,
    }
    TAXONOMY_COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TAXONOMY_COVERAGE_PATH.write_text(json.dumps(coverage, indent=2), encoding="utf-8")

    return {
        "status": "rebuilt",
        "index_path": str(INDEX_PATH),
        "coverage_path": str(TAXONOMY_COVERAGE_PATH),
        **coverage["summary"],
    }


def walkthrough_library(limit: int = 1000) -> dict:
    index = load_index()
    if not index.get("walkthroughs"):
        rebuild_walkthrough_index_from_storage()
        index = load_index()

    taxonomy = load_search_phrase_taxonomy()
    coverage = load_taxonomy_coverage()
    records = index.get("walkthroughs", {}) or {}
    taxonomy_entries = taxonomy.get("walkthroughs", {}) or {}
    status_counts = {}
    quality_counts = {}
    category_counts = {}
    stored_items = []

    for walkthrough_id, record in sorted(
        records.items(),
        key=lambda item: (item[1].get("review_status", ""), item[1].get("title", ""))
    ):
        review_status = record.get("review_status", "draft")
        quality_status = record.get("quality_status", "unvalidated")
        category = record.get("taxonomy_category") or record.get("category") or "generic"
        taxonomy_id = record.get("taxonomy_walkthrough_id", "")
        taxonomy_entry = taxonomy_entries.get(taxonomy_id, {}) if taxonomy_id else {}

        status_counts[review_status] = status_counts.get(review_status, 0) + 1
        quality_counts[quality_status] = quality_counts.get(quality_status, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

        stored_items.append({
            "walkthrough_id": walkthrough_id,
            "storage_walkthrough_id": record.get("storage_walkthrough_id", walkthrough_id),
            "manifest_walkthrough_id": record.get("manifest_walkthrough_id", ""),
            "title": record.get("title", walkthrough_id),
            "canonical_query": record.get("canonical_query", ""),
            "category": category,
            "review_status": review_status,
            "quality_status": quality_status,
            "step_count": record.get("step_count", 0),
            "image_count": record.get("image_count", 0),
            "taxonomy_walkthrough_id": taxonomy_id,
            "taxonomy_title": record.get("taxonomy_title", taxonomy_entry.get("title", "")),
            "taxonomy_match_score": record.get("taxonomy_match_score", 0),
            "coverage_status": "matched_taxonomy" if taxonomy_id else "unmatched_existing",
            "requires_branch_selection": bool(taxonomy_entry.get("requires_branch_selection")),
            "branch_question": taxonomy_entry.get("branch_question", ""),
            "branches": taxonomy_entry.get("branches", []) or [],
            "aliases": record.get("aliases", []) or [],
        })

    covered_taxonomy_ids = {
        item.get("taxonomy_walkthrough_id", "")
        for item in stored_items
        if item.get("taxonomy_walkthrough_id")
    }
    prospective_items = []
    for taxonomy_id, entry in sorted(taxonomy_entries.items()):
        resolved_id = entry.get("walkthrough_id") or taxonomy_id
        if resolved_id in covered_taxonomy_ids or taxonomy_id in covered_taxonomy_ids:
            continue
        prospective_items.append({
            "taxonomy_walkthrough_id": resolved_id,
            "title": entry.get("title", resolved_id),
            "canonical_query": entry.get("canonical_query", ""),
            "category": entry.get("category", "generic"),
            "safety_level": entry.get("safety_level", "standard"),
            "requires_branch_selection": bool(entry.get("requires_branch_selection")),
            "branch_question": entry.get("branch_question", ""),
            "branches": entry.get("branches", []) or [],
            "alias_count": len(entry.get("aliases", []) or []),
        })

    stored_items = stored_items[:max(1, min(limit, 5000))]
    prospective_items = prospective_items[:max(1, min(limit, 5000))]

    return {
        "status": "loaded",
        "summary": {
            "stored_walkthrough_count": len(records),
            "taxonomy_entry_count": len(taxonomy_entries),
            "taxonomy_entries_with_existing_walkthroughs": len(covered_taxonomy_ids),
            "prospective_taxonomy_entries_without_existing_walkthroughs": max(
                0,
                len(taxonomy_entries) - len(covered_taxonomy_ids)
            ),
            "unmatched_existing_walkthrough_count": len([
                item for item in stored_items if item.get("coverage_status") == "unmatched_existing"
            ]),
            "coverage_file_unmatched_count": len(coverage.get("unmatched_existing_walkthroughs", []) or []),
            "error_count": len(coverage.get("errors", []) or []),
            "status_counts": status_counts,
            "quality_counts": quality_counts,
            "category_counts": category_counts,
        },
        "stored_walkthroughs": stored_items,
        "prospective_walkthroughs": prospective_items,
        "errors": coverage.get("errors", []) or [],
    }


def find_walkthrough_id_for_query(query: str) -> str:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return ""

    index = load_index()
    records = index.get("walkthroughs", {})

    for walkthrough_id, record in records.items():
        if record.get("review_status") in ["deleted", "deprecated"]:
            continue
        aliases = record.get("aliases", []) or []
        if normalized_query in aliases:
            return walkthrough_id

    query_terms = set(normalized_query.split())
    if len(query_terms) < 2:
        return ""

    best_id = ""
    best_score = 0

    for walkthrough_id, record in records.items():
        if record.get("review_status") in ["deleted", "deprecated"]:
            continue
        aliases = record.get("aliases", []) or []
        for alias in aliases:
            score = alias_similarity(normalized_query, alias)
            if score > best_score:
                best_id = walkthrough_id
                best_score = score

    return best_id if best_score >= 0.72 else ""
