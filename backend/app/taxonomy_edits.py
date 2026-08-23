import hashlib
import time

try:
    from app.metadata_repository import metadata_repository
except ImportError:
    from metadata_repository import metadata_repository

try:
    from app.walkthrough_index import find_taxonomy_match_for_manifest, normalize_search_text
except ImportError:
    from walkthrough_index import find_taxonomy_match_for_manifest, normalize_search_text


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_query_alias_candidate(
    walkthrough_id: str,
    manifest_before: dict,
    manifest_after: dict,
    source: str = "qc_query_edit",
) -> dict | None:
    before_query = (manifest_before or {}).get("query", "")
    after_query = (manifest_after or {}).get("query", "")
    after_title = (manifest_after or {}).get("title", "")
    normalized_query = normalize_search_text(after_query)

    if not normalized_query:
        return None
    if normalize_search_text(before_query) == normalized_query:
        return None

    taxonomy_match = find_taxonomy_match_for_manifest(manifest_after or {}, walkthrough_id)
    record_id = hashlib.sha1(
        f"{walkthrough_id}|{normalized_query}".encode("utf-8")
    ).hexdigest()[:16]
    record = {
        "schema_version": 1,
        "source": source,
        "status": "candidate",
        "walkthrough_id": walkthrough_id,
        "previous_query": before_query,
        "proposed_query": after_query,
        "normalized_query": normalized_query,
        "title": after_title,
        "taxonomy_walkthrough_id": taxonomy_match.get("taxonomy_walkthrough_id", ""),
        "taxonomy_canonical_query": taxonomy_match.get("taxonomy_canonical_query", ""),
        "taxonomy_title": taxonomy_match.get("taxonomy_title", ""),
        "taxonomy_category": taxonomy_match.get("taxonomy_category", ""),
        "taxonomy_match_score": taxonomy_match.get("taxonomy_match_score", 0),
        "created_at": now_iso(),
        "notes": "Created from an editor query rewrite. Review before merging into curated taxonomy aliases.",
    }
    return metadata_repository.upsert_record("taxonomy_alias_candidates", record_id, record)

