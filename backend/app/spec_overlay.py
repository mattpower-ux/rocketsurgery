import json

try:
    from app.catalog import load_product_options
except ImportError:
    from catalog import load_product_options


OVERLAY_RULES = {
    "bidets": [
        {
            "keywords": ["electrical", "heated seat"],
            "type": "warning",
            "title": "Electrical Receptacle Required",
            "content": (
                "Many bidet seats require a nearby GFCI receptacle. "
                "Verify outlet location and amperage before installation."
            )
        }
    ],

    "heat pump water heaters": [
        {
            "keywords": ["condensate"],
            "type": "extra_step",
            "title": "Condensate Drain Required",
            "content": (
                "Heat pump water heaters require condensate drainage. "
                "Plan drain routing before final placement."
            )
        }
    ],

    "tankless water heaters": [
        {
            "keywords": ["gas line", "venting"],
            "type": "warning",
            "title": "Gas + Venting Verification",
            "content": (
                "Tankless units may require upgraded gas supply "
                "and manufacturer-approved venting."
            )
        }
    ],

    "composite decking": [
        {
            "keywords": ["hidden fastener"],
            "type": "extra_step",
            "title": "Hidden Fastener Layout",
            "content": (
                "Some decking systems require starter clips "
                "and hidden fastener spacing unique to the product."
            )
        }
    ]
}


def normalize(text: str) -> str:
    return text.lower().strip()


def detect_category(query: str, category: str = ""):
    if category:
        return normalize(category)

    q = normalize(query)

    catalog = load_product_options()

    for category_slug, data in catalog.items():
        keywords = data.get("keywords", [])

        for keyword in keywords:
            if normalize(keyword) in q:
                return category_slug

    return "generic"


def build_spec_overlay(
    query: str,
    category: str = "",
    brand: str = "",
    model: str = "",
    extracted_specs: dict | None = None
):
    category_slug = detect_category(query, category)

    overlays = []

    category_rules = OVERLAY_RULES.get(category_slug, [])

    for rule in category_rules:
        overlays.append({
            "type": rule["type"],
            "title": rule["title"],
            "content": rule["content"],
            "source": "generic_category_rule"
        })

    specs = extracted_specs or {}

    if specs.get("electrical_required"):
        overlays.append({
            "type": "warning",
            "title": "Electrical Requirement",
            "content": (
                "Manufacturer specs indicate dedicated electrical "
                "requirements for this product."
            ),
            "source": "manual_spec"
        })

    if specs.get("special_tools"):
        overlays.append({
            "type": "tooling",
            "title": "Special Tools Required",
            "content": ", ".join(specs["special_tools"]),
            "source": "manual_spec"
        })

    if specs.get("critical_clearance"):
        overlays.append({
            "type": "clearance",
            "title": "Critical Clearance",
            "content": specs["critical_clearance"],
            "source": "manual_spec"
        })

    return {
        "query": query,
        "category": category_slug,
        "brand": brand,
        "model": model,
        "overlay_count": len(overlays),
        "overlays": overlays
    }
