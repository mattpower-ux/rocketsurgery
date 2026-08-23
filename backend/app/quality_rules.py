import json

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR


INTELLIGENCE_DIR = BASE_DIR / "intelligence"
CATEGORY_RULES_FILE = INTELLIGENCE_DIR / "category_rules.json"


def infer_construction_category(walkthrough_id: str = "", title: str = "", query: str = "") -> str:
    blob = f"{walkthrough_id} {title} {query}".lower()
    if any(term in blob for term in ["tile shower", "shower pan", "shower base", "shower"]):
        return "tile_shower"
    if any(term in blob for term in ["toilet", "commode", "water closet"]):
        return "toilet"
    if any(term in blob for term in ["siding", "hardie", "fiber cement"]):
        return "siding"
    if any(term in blob for term in ["water heater", "tankless"]):
        return "water_heater"
    if any(term in blob for term in ["heat pump", "mini split", "hvac"]):
        return "heat_pump"
    if any(term in blob for term in ["solar", "panel", "inverter"]):
        return "solar"
    return "generic"


def load_category_rules() -> dict:
    if not CATEGORY_RULES_FILE.exists():
        return {}
    try:
        return json.loads(CATEGORY_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def category_rules_for(category: str) -> dict:
    rules = load_category_rules()
    value = rules.get(category or "generic", {})
    return value if isinstance(value, dict) else {}


def format_rules_for_prompt(category: str) -> str:
    rules = category_rules_for(category)
    must_show = rules.get("must_show", []) or []
    must_not_show = rules.get("must_not_show", []) or []
    step_order = rules.get("step_order", []) or []
    common_errors = rules.get("common_errors", []) or []

    parts = []
    if step_order:
        parts.append("Preferred order: " + "; ".join(str(item) for item in step_order[:10]) + ".")
    if must_show:
        parts.append("Must show: " + "; ".join(str(item) for item in must_show[:8]) + ".")
    if must_not_show:
        parts.append("Must not show: " + "; ".join(str(item) for item in must_not_show[:8]) + ".")
    if common_errors:
        parts.append("Avoid these known errors: " + "; ".join(str(item) for item in common_errors[:8]) + ".")

    return " ".join(parts)
