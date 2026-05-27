import json

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify


CATALOG_DIR = BASE_DIR / "catalog"
ADMIN_DIR = BASE_DIR / "admin"

PRODUCT_OPTIONS_FILE = CATALOG_DIR / "product-options.json"
CANONICAL_QUEUE_FILE = ADMIN_DIR / "canonical-walkthroughs.json"


CATEGORY_QUERY_MAP = {
    "toilets": "replace toilet",
    "faucets": "replace kitchen faucet",
    "plumbing fixtures": "replace plumbing fixture",
    "bidets": "install bidet",
    "dishwashers": "install dishwasher",
    "refrigerators": "install refrigerator",
    "freezers": "install freezer",
    "induction ranges": "install induction range",
    "heat pump water heaters": "install heat pump water heater",
    "tankless water heaters": "install tankless water heater",
    "water softeners": "install water softener",
    "air handlers": "install air handler",
    "hvac": "service hvac system",
    "ventilation fans": "install bathroom exhaust fan",
    "energy recovery ventilators": "install erv",
    "siding": "install siding",
    "trim": "install exterior trim",
    "metal roofing": "install metal roofing",
    "roofing": "install roofing",
    "composite decking": "install composite decking",
    "pvc decking": "install pvc decking",
    "wood decking": "install wood decking",
    "windows & doors": "install window or door",
    "doors": "install door",
    "garage doors": "install garage door",
    "insulation": "install insulation",
    "smart thermostats": "install smart thermostat",
    "smart switches": "install smart switch",
    "electrical equipment": "install electrical equipment",
    "smart electrical panels": "install smart electrical panel",
    "home battery storage": "install home battery system",
    "solar panels": "install solar panels",
    "flooring": "install flooring",
    "tile": "install tile",
    "countertops": "install countertop",
    "cabinetry": "install cabinets",
    "paint": "paint interior wall"
}


def load_json(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data


def category_to_query(category: str) -> str:
    clean = category.lower().strip()

    if clean in CATEGORY_QUERY_MAP:
        return CATEGORY_QUERY_MAP[clean]

    singular = clean[:-1] if clean.endswith("s") else clean

    if singular in CATEGORY_QUERY_MAP:
        return CATEGORY_QUERY_MAP[singular]

    return f"install {singular}"


def seed_canonical_walkthroughs():
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})
    existing = load_json(CANONICAL_QUEUE_FILE, {"walkthroughs": []})

    existing_slugs = {
        item.get("query_slug")
        for item in existing.get("walkthroughs", [])
    }

    added = []

    for category_slug, data in product_options.items():
        category_name = category_slug.replace("-", " ")
        query = category_to_query(category_name)
        query_slug = slugify(query)

        if query_slug in existing_slugs:
            continue

        record = {
            "query": query,
            "query_slug": query_slug,
            "source_category": category_slug,
            "status": "queued",
            "priority": "category_canonical",
            "generation_mode": "generic_first"
        }

        existing["walkthroughs"].append(record)
        existing_slugs.add(query_slug)
        added.append(record)

    save_json(CANONICAL_QUEUE_FILE, existing)

    return {
        "status": "canonical walkthrough queue seeded",
        "added_count": len(added),
        "total_count": len(existing["walkthroughs"]),
        "added": added
    }
