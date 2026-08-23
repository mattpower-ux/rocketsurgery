import json
import re
import time
from pathlib import Path

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR

try:
    from app.quality_rules import infer_construction_category
except ImportError:
    from quality_rules import infer_construction_category


INTELLIGENCE_DIR = BASE_DIR / "intelligence"
CATEGORY_RULES_FILE = INTELLIGENCE_DIR / "category_rules.json"
EDITOR_LEARNING_FILE = INTELLIGENCE_DIR / "editor_learning_events.jsonl"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_rules() -> dict:
    if not CATEGORY_RULES_FILE.exists():
        return {}
    try:
        data = json.loads(CATEGORY_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def save_rules(rules: dict) -> dict:
    INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORY_RULES_FILE.write_text(json.dumps(rules, indent=2), encoding="utf-8")
    return rules


def append_learning_event(payload: dict):
    INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "created_at": now_iso(),
        **(payload or {}),
    }
    with EDITOR_LEARNING_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def compact_phrase(value: str, max_words: int = 8) -> str:
    text = re.sub(r"^step\s+\d+\s*:\s*", "", str(value or ""), flags=re.IGNORECASE)
    text = re.sub(r"[^a-zA-Z0-9 /+-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def step_learning_phrase(step: dict) -> str:
    return compact_phrase(
        step.get("imageLabel")
        or step.get("instruction")
        or step.get("detail")
        or ""
    )


def merge_unique(existing: list, additions: list, limit: int = 40) -> list:
    seen = set()
    merged = []
    for value in [*(existing or []), *(additions or [])]:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        merged.append(text)
        if len(merged) >= limit:
            break
    return merged


def extract_image_rule_phrases(steps: list[dict]) -> tuple[list[str], list[str]]:
    must_show = []
    must_not_show = []
    negative_markers = ["do not", "don't", "avoid", "without", "not show", "no "]

    for step in steps or []:
        direction = re.sub(r"\s+", " ", str(step.get("imageDirection") or "").strip())
        if not direction:
            continue
        target = must_not_show if any(marker in direction.lower() for marker in negative_markers) else must_show
        target.append(direction[:220].rstrip(" ,;:-"))

    return must_show, must_not_show


def changed_step_summaries(before_steps: list[dict], after_steps: list[dict]) -> list[str]:
    summaries = []
    for index, after_step in enumerate(after_steps or []):
        before_step = (before_steps or [])[index] if index < len(before_steps or []) else {}
        before_text = compact_phrase(
            before_step.get("instruction")
            or before_step.get("imageLabel")
            or before_step.get("detail")
            or ""
        )
        after_text = compact_phrase(
            after_step.get("instruction")
            or after_step.get("imageLabel")
            or after_step.get("detail")
            or ""
        )
        if before_text and after_text and before_text != after_text:
            summaries.append(f"Prefer '{after_text}' over '{before_text}'.")
    return summaries


def category_for_edit(before: dict, after: dict) -> str:
    source = after or before or {}
    return infer_construction_category(
        walkthrough_id=source.get("walkthrough_id", ""),
        title=source.get("title", ""),
        query=source.get("query", ""),
    )


def learn_from_walkthrough_edit(action: str, before: dict, after: dict, context: dict | None = None) -> dict:
    before = before or {}
    after = after or {}
    context = context or {}
    category = category_for_edit(before, after)
    rules = load_rules()
    category_rules = dict(rules.get(category, {}) if isinstance(rules.get(category), dict) else {})

    after_steps = after.get("steps", []) or []
    before_steps = before.get("steps", []) or []
    learned_order = [
        phrase for phrase in [step_learning_phrase(step) for step in after_steps]
        if phrase
    ]
    must_show, must_not_show = extract_image_rule_phrases(after_steps)
    common_errors = changed_step_summaries(before_steps, after_steps)

    category_rules["step_order"] = merge_unique(
        category_rules.get("step_order", []),
        learned_order,
        limit=36,
    )
    category_rules["must_show"] = merge_unique(
        category_rules.get("must_show", []),
        must_show,
        limit=30,
    )
    category_rules["must_not_show"] = merge_unique(
        category_rules.get("must_not_show", []),
        must_not_show,
        limit=30,
    )
    category_rules["common_errors"] = merge_unique(
        category_rules.get("common_errors", []),
        common_errors,
        limit=30,
    )
    category_rules["learned_example_count"] = int(category_rules.get("learned_example_count", 0) or 0) + 1
    category_rules["updated_at"] = now_iso()
    category_rules["last_action"] = action

    rules[category] = category_rules
    save_rules(rules)

    event = append_learning_event({
        "action": action,
        "category": category,
        "walkthrough_id": after.get("walkthrough_id") or before.get("walkthrough_id", ""),
        "title": after.get("title") or before.get("title", ""),
        "query": after.get("query") or before.get("query", ""),
        "learned_step_order_count": len(learned_order),
        "learned_must_show_count": len(must_show),
        "learned_must_not_show_count": len(must_not_show),
        "learned_common_error_count": len(common_errors),
        "context": context,
    })

    return {
        "status": "learned",
        "category": category,
        "rules": category_rules,
        "event": event,
    }
