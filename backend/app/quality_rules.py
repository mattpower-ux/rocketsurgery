import json

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR


INTELLIGENCE_DIR = BASE_DIR / "intelligence"
CATEGORY_RULES_FILE = INTELLIGENCE_DIR / "category_rules.json"


def infer_construction_category(walkthrough_id: str = "", title: str = "", query: str = "") -> str:
    blob = f"{walkthrough_id} {title} {query}".lower()
    if any(term in blob for term in ["shower cartridge", "valve cartridge", "mixing cartridge", "temperature control cartridge"]):
        return "shower_cartridge"
    if any(term in blob for term in ["replace shower valve", "install shower valve", "shower valve body", "concealed shower valve", "mixing valve"]):
        return "shower_valve"
    if any(term in blob for term in ["acrylic shower", "fiberglass shower", "prefab shower", "shower kit", "shower surround"]):
        return "prefab_shower"
    if any(term in blob for term in ["shower head", "showerhead", "shower arm", "shower fixture"]):
        return "shower_fixture"
    if any(term in blob for term in ["bathroom sink", "vanity sink", "bathroom basin", "sink replacement"]):
        return "plumbing_sink"
    if any(term in blob for term in ["gfci", "outlet", "switch", "breaker", "wire", "wiring", "electrical"]):
        return "electrical"
    if any(term in blob for term in ["insulation", "attic insulation", "spray foam"]):
        return "insulation"
    if any(term in blob for term in ["dishwasher"]):
        return "dishwasher"
    if any(term in blob for term in ["faucet", "sink fixture"]):
        return "faucet"
    if any(term in blob for term in ["chimney cap", "chimney crown", "chimney flue"]):
        return "chimney_cap"
    if any(term in blob for term in ["roof", "shingle", "flashing"]):
        return "roofing"
    if any(term in blob for term in ["window", "door", "sash", "sliding glass"]):
        return "door_window"
    if any(term in blob for term in ["floor", "flooring", "hardwood", "laminate", "vinyl plank"]):
        return "flooring"
    if any(term in blob for term in ["tile shower", "tile a shower", "shower tile", "grout shower", "shower mortar bed"]):
        return "tile_shower"
    if any(term in blob for term in ["toilet", "commode", "water closet"]):
        return "toilet"
    if any(term in blob for term in ["siding", "hardie", "fiber cement"]):
        return "siding"
    if any(term in blob for term in ["water heater", "tankless"]):
        return "water_heater"
    if any(term in blob for term in ["heat pump", "mini split", "hvac"]):
        return "heat_pump"
    if any(term in blob for term in ["solar panel", "pv panel", "photovoltaic", "solar inverter", "solar array"]):
        return "solar"
    return "generic"


def load_category_rules() -> dict:
    if not CATEGORY_RULES_FILE.exists():
        return {}
    try:
        return json.loads(CATEGORY_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_category_rules(rules: dict) -> dict:
    INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORY_RULES_FILE.write_text(json.dumps(rules or {}, indent=2), encoding="utf-8")
    return rules or {}


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
    if must_show:
        parts.append("Must show: " + "; ".join(str(item) for item in must_show[:8]) + ".")
    if must_not_show:
        parts.append("Must not show: " + "; ".join(str(item) for item in must_not_show[:8]) + ".")
    if step_order:
        parts.append("Preferred step logic: " + "; ".join(str(item) for item in step_order[:10]) + ".")
    if common_errors:
        parts.append("Avoid these known errors: " + "; ".join(str(item) for item in common_errors[:8]) + ".")

    return " ".join(parts)
