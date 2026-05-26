import json
from pathlib import Path

from openai import OpenAI
import os

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

CATALOG_DIR = BASE_DIR / "catalog"
CATALOG_REQUESTS_FILE = CATALOG_DIR / "catalog-requests.json"
PRODUCT_OPTIONS_FILE = CATALOG_DIR / "product-options.json"


SYSTEM_PROMPT = """
You help build a product model discovery queue for a contractor installation app.

Return ONLY valid JSON.

Given a brand and product category, suggest likely model names or model families that contractors commonly encounter.

Rules:
- Return up to 10 model names or model families.
- Do not invent exact model numbers unless they are widely known.
- Prefer model families if exact models are uncertain.
- No markdown.
- No explanation.

Return format:
{
  "models": [
    "model or model family"
  ]
}
"""


def load_json(path: Path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data


def discover_models_for_brand_category(brand: str, category: str) -> list:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Brand: {brand}\nCategory: {category}"
            }
        ]
    )

    raw = response.choices[0].message.content

    try:
      parsed = json.loads(raw)
      models = parsed.get("models", [])

      if isinstance(models, list):
          return [str(model).strip() for model in models if str(model).strip()][:10]

    except Exception:
      pass

    return []


def update_product_options_with_models(brand: str, category: str, models: list):
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})

    category_slug = category.lower().strip().replace(" ", "-")

    if category_slug not in product_options:
        product_options[category_slug] = {
            "keywords": [
                category.lower(),
                category_slug.replace("-", " ")
            ],
            "brands": []
        }

    brands = product_options[category_slug].setdefault("brands", [])

    existing_brand = None

    for brand_entry in brands:
        if brand_entry.get("brand", "").lower() == brand.lower():
            existing_brand = brand_entry
            break

    if existing_brand is None:
        existing_brand = {
            "brand": brand,
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


def process_model_discovery(limit: int = 5):
    requests = load_json(CATALOG_REQUESTS_FILE, {"requests": []})
    items = requests.get("requests", [])

    queued = [
        item for item in items
        if item.get("status") == "queued_for_model_discovery"
    ]

    processed = []
    failed = []

    for item in queued[:limit]:
        brand = item.get("brand", "")
        category = item.get("category", "")

        try:
            models = discover_models_for_brand_category(brand, category)

            update_product_options_with_models(
                brand=brand,
                category=category,
                models=models
            )

            item["models"] = models
            item["status"] = "model_discovery_completed"
            item["discovered_model_count"] = len(models)

            processed.append({
                "brand": brand,
                "category": category,
                "models": models
            })

        except Exception as e:
            item["status"] = "model_discovery_failed"
            item["error": str(e)]

            failed.append({
                "brand": brand,
                "category": category,
                "error": str(e)
            })

    save_json(CATALOG_REQUESTS_FILE, requests)

    return {
        "status": "model discovery complete",
        "processed_count": len(processed),
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
        "remaining_queued": len([
            item for item in items
            if item.get("status") == "queued_for_model_discovery"
        ])
    }
