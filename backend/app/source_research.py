import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from openai import OpenAI

try:
    from app.config import BASE_DIR
    from app.storage import query_to_walkthrough_id
except ImportError:
    from config import BASE_DIR
    from storage import query_to_walkthrough_id


SOURCE_RESEARCH_DIR = BASE_DIR / "source-research"
SOURCE_RESEARCH_EVENTS_FILE = BASE_DIR / "intelligence" / "source_research_events.jsonl"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
MAX_CANDIDATES = 5

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


RESEARCH_SYNTHESIS_PROMPT = """
You help improve contractor walkthrough generation.

You will receive a home repair or installation query and brief public video
metadata found during discovery. Use the metadata only as background signal.
Do not quote, cite, or imitate any source. Return original, concise JSON.

Return this exact shape:
{
  "required_steps": ["..."],
  "common_mistakes": ["..."],
  "image_guidance": ["..."],
  "branch_questions": ["..."],
  "tools_and_materials": ["..."]
}

Rules:
- Include only actionable how-to information.
- Prefer sequence, visual, safety, and setup details that make a walkthrough clearer.
- Do not include source names, channel names, links, quotes, or transcript text.
- Keep each array to 8 items or fewer.
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def source_research_path(query: str) -> Path:
    return SOURCE_RESEARCH_DIR / f"{query_to_walkthrough_id(query)}.json"


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def append_event(payload: dict):
    try:
        SOURCE_RESEARCH_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {"created_at": now_iso(), **(payload or {})}
        with SOURCE_RESEARCH_EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print("Source research event write failed:", exc)


def youtube_search(query: str, limit: int = MAX_CANDIDATES) -> list[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GOOGLE_YOUTUBE_API_KEY")
    if not api_key:
        return []

    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": str(max(1, min(limit, MAX_CANDIDATES))),
        "q": f"{query} how to installation repair walkthrough",
        "key": api_key,
        "safeSearch": "strict",
        "videoEmbeddable": "true",
    }
    url = f"{YOUTUBE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "RocketSurgeryResearch/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))

    candidates = []
    for item in data.get("items", []) or []:
        snippet = item.get("snippet", {}) or {}
        candidates.append({
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
        })
    return candidates


def normalized_list(value, limit: int = 8) -> list:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()][:limit]


def synthesize_research_brief(query: str, candidates: list[dict]) -> dict:
    if not candidates:
        return {
            "required_steps": [],
            "common_mistakes": [],
            "image_guidance": [],
            "branch_questions": [],
            "tools_and_materials": [],
        }

    compact_candidates = [
        {
            "title": str(item.get("title", ""))[:180],
            "description": str(item.get("description", ""))[:320],
        }
        for item in candidates[:MAX_CANDIDATES]
    ]
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": RESEARCH_SYNTHESIS_PROMPT},
            {
                "role": "user",
                "content": json.dumps({
                    "query": query,
                    "public_video_metadata": compact_candidates,
                }, ensure_ascii=False),
            },
        ],
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}

    return {
        "required_steps": normalized_list(parsed.get("required_steps", [])),
        "common_mistakes": normalized_list(parsed.get("common_mistakes", [])),
        "image_guidance": normalized_list(parsed.get("image_guidance", [])),
        "branch_questions": normalized_list(parsed.get("branch_questions", [])),
        "tools_and_materials": normalized_list(parsed.get("tools_and_materials", [])),
    }


def discover_source_research(query: str, force_refresh: bool = False) -> dict:
    clean_query = " ".join((query or "").split())
    path = source_research_path(clean_query)
    cached = read_json(path, {})
    if cached and not force_refresh:
        return cached

    status = "researched"
    error = ""
    candidates = []
    try:
        youtube_key_available = bool(os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GOOGLE_YOUTUBE_API_KEY"))
        candidates = youtube_search(clean_query)
        if not youtube_key_available:
            status = "skipped_no_youtube_api_key"
        elif not candidates:
            status = "no_sources_found"
        brief = synthesize_research_brief(clean_query, candidates)
    except Exception as exc:
        status = "research_failed"
        error = str(exc)
        brief = synthesize_research_brief(clean_query, [])

    record = {
        "schema_version": 1,
        "query": clean_query,
        "walkthrough_id": query_to_walkthrough_id(clean_query),
        "status": status,
        "researched_at": now_iso(),
        "source_types": ["youtube_public_metadata"] if candidates else [],
        "source_candidate_count": len(candidates),
        "brief": brief,
    }
    if error:
        record["error"] = error

    write_json(path, record)
    append_event({
        "action": "source_research_discovered",
        "query": clean_query,
        "walkthrough_id": record["walkthrough_id"],
        "status": status,
        "source_candidate_count": len(candidates),
    })
    return record


def format_research_for_planner(research: dict) -> str:
    brief = (research or {}).get("brief", {}) or {}
    parts = []
    if brief.get("required_steps"):
        parts.append("Required sequence signals: " + "; ".join(map(str, brief["required_steps"][:8])) + ".")
    if brief.get("common_mistakes"):
        parts.append("Avoid common mistakes: " + "; ".join(map(str, brief["common_mistakes"][:8])) + ".")
    if brief.get("branch_questions"):
        parts.append("Clarify branches when relevant: " + "; ".join(map(str, brief["branch_questions"][:5])) + ".")
    if brief.get("tools_and_materials"):
        parts.append("Likely tools/materials: " + "; ".join(map(str, brief["tools_and_materials"][:8])) + ".")
    return " ".join(parts)


def format_research_for_image_prompt(research: dict) -> str:
    brief = (research or {}).get("brief", {}) or {}
    guidance = brief.get("image_guidance", []) or []
    if not guidance:
        return ""
    return "Research-backed image guidance: " + "; ".join(map(str, guidance[:5])) + "."
