import json
from datetime import datetime, timezone

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify


ADMIN_DIR = BASE_DIR / "admin"
CATALOG_DIR = BASE_DIR / "catalog"

BULK_QUERIES_FILE = ADMIN_DIR / "bulk-queries.json"
CATALOG_REQUESTS_FILE = CATALOG_DIR / "catalog-requests.json"
PRODUCT_OPTIONS_FILE = CATALOG_DIR / "product-options.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_admin_storage():
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    if not BULK_QUERIES_FILE.exists():
        BULK_QUERIES_FILE.write_text(
            json.dumps({"queries": []}, indent=2),
            encoding="utf-8"
        )

    if not CATALOG_REQUESTS_FILE.exists():
        CATALOG_REQUESTS_FILE.write_text(
            json.dumps({"requests": []}, indent=2),
            encoding="utf-8"
        )


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


def save_bulk_queries(raw_text: str):
    ensure_admin_storage()

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    existing = load_json(BULK_QUERIES_FILE, {"queries": []})
    existing_queries = existing.get("queries", [])

    existing_texts = {
        item.get("query", "").lower()
        for item in existing_queries
    }

    added = []

    for line in lines:
        normalized = line.lower()

        if normalized in existing_texts:
            continue

        record = {
            "query": line,
            "query_slug": slugify(line),
            "status": "queued",
            "created_at": now_iso()
        }

        existing_queries.append(record)
        existing_texts.add(normalized)
        added.append(record)

    existing["queries"] = existing_queries
    save_json(BULK_QUERIES_FILE, existing)

    return {
        "status": "saved",
        "submitted_count": len(lines),
        "added_count": len(added),
        "duplicate_count": len(lines) - len(added),
        "total_count": len(existing_queries),
        "added": added
    }


def save_catalog_request(
    brand: str,
    category: str,
    models_text: str = "",
    discover_top_models: bool = True
):
    ensure_admin_storage()

    brand = brand.strip()
    category = category.strip()

    models = [
        line.strip()
        for line in models_text.splitlines()
        if line.strip()
    ]

    request_record = {
        "brand": brand,
        "brand_slug": slugify(brand),
        "category": category,
        "category_slug": slugify(category),
        "models": models,
        "discover_top_models": discover_top_models and len(models) == 0,
        "requested_model_count": 10 if discover_top_models and len(models) == 0 else len(models),
        "status": "queued_for_model_discovery" if discover_top_models and len(models) == 0 else "models_supplied",
        "created_at": now_iso()
    }

    requests = load_json(CATALOG_REQUESTS_FILE, {"requests": []})
    requests["requests"].append(request_record)
    save_json(CATALOG_REQUESTS_FILE, requests)

    update_product_options_from_catalog_request(request_record)

    return {
        "status": "saved",
        "request": request_record
    }


def update_product_options_from_catalog_request(request_record: dict):
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})

    category_slug = request_record["category_slug"]
    category_name = request_record["category"]

    if category_slug not in product_options:
        product_options[category_slug] = {
            "keywords": [
                category_name.lower(),
                category_slug.replace("-", " ")
            ],
            "brands": []
        }

    brands = product_options[category_slug].setdefault("brands", [])

    brand_name = request_record["brand"]
    models = request_record.get("models", [])

    existing_brand = None

    for brand_entry in brands:
        if brand_entry.get("brand", "").lower() == brand_name.lower():
            existing_brand = brand_entry
            break

    if existing_brand is None:
        existing_brand = {
            "brand": brand_name,
            "models": []
        }
        brands.append(existing_brand)

    existing_models = {
        model.lower()
        for model in existing_brand.get("models", [])
    }

    for model in models:
        if model.lower() not in existing_models:
            existing_brand["models"].append(model)

    save_json(PRODUCT_OPTIONS_FILE, product_options)

    return product_options


def admin_status():
    ensure_admin_storage()

    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    requests = load_json(CATALOG_REQUESTS_FILE, {"requests": []})
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})

    return {
        "status": "admin storage ready",
        "bulk_query_count": len(bulk.get("queries", [])),
        "catalog_request_count": len(requests.get("requests", [])),
        "catalog_category_count": len(product_options.keys())
    }
