import json
import re
from pathlib import Path

try:
    from app.walkthrough_index import normalize_search_text
except ImportError:
    from walkthrough_index import normalize_search_text


TAXONOMY_PATH = Path(__file__).with_name("search_phrase_taxonomy.json")


def load_taxonomy() -> dict:
    if not TAXONOMY_PATH.exists():
        return {"walkthroughs": {}}

    try:
        data = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("walkthroughs", {})
    return data


def taxonomy_aliases(entry: dict) -> list[str]:
    values = [
        entry.get("walkthrough_id", ""),
        entry.get("canonical_query", ""),
        entry.get("title", ""),
        *(entry.get("aliases", []) or []),
    ]
    return sorted({
        normalized
        for normalized in [normalize_search_text(value) for value in values]
        if normalized
    })


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


def classify_taxonomy_query(query: str) -> dict:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return {"status": "unmatched"}

    best_entry = None
    best_id = ""
    best_score = 0

    for taxonomy_id, entry in load_taxonomy().get("walkthroughs", {}).items():
        for alias in taxonomy_aliases({
            **entry,
            "walkthrough_id": entry.get("walkthrough_id") or taxonomy_id,
        }):
            score = alias_similarity(normalized_query, alias)
            if score > best_score:
                best_id = entry.get("walkthrough_id") or taxonomy_id
                best_entry = entry
                best_score = score

    if not best_entry or best_score < 0.72:
        return {"status": "unmatched"}

    response = {
        "status": "matched",
        "walkthrough_id": best_id,
        "canonical_query": best_entry.get("canonical_query", ""),
        "title": best_entry.get("title", ""),
        "category": best_entry.get("category", ""),
        "match_score": round(best_score, 3),
    }

    if best_entry.get("requires_branch_selection"):
        response.update({
            "status": "branch_selection_required",
            "question": best_entry.get("branch_question", "Which type of walkthrough do you need?"),
            "branches": best_entry.get("branches", []) or [],
        })

    return response


def query_requires_branch_selection(query: str) -> bool:
    return classify_taxonomy_query(query).get("status") == "branch_selection_required"


def branch_query(base_query: str, branch: dict) -> str:
    query = branch.get("query") or branch.get("target_walkthrough_id") or base_query
    return re.sub(r"\s+", " ", query).strip()
