import json
from pathlib import Path

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


CATALOG_DIR = BASE_DIR / "catalog"
PRODUCT_OPTIONS_FILE = CATALOG_DIR / "product-options.json"


DEFAULT_PRODUCT_OPTIONS = {
    "shower-cartridge": {
        "keywords": [
            "shower cartridge",
            "replace shower cartridge",
            "cartridge",
            "shower valve"
        ],
        "brands": [
            {
                "brand": "Moen",
                "models": [
                    "1222 Posi-Temp",
                    "1225 Cartridge",
                    "1200 Cartridge",
                    "M-Core 1213",
                    "Flo Smart Valve"
                ]
            },
            {
                "brand": "Delta",
                "models": [
                    "RP19804",
                    "RP46074",
                    "Monitor 14 Series",
                    "MultiChoice Universal",
                    "RP50587"
                ]
            },
            {
                "brand": "Kohler",
                "models": [
                    "GP500520",
                    "GP76851",
                    "GP800820",
                    "Rite-Temp",
                    "K-8304"
                ]
            },
            {
                "brand": "Pfister",
                "models": [
                    "974-042",
                    "974-074",
                    "974-292",
                    "974-321",
                    "Avante Cartridge"
                ]
            },
            {
                "brand": "American Standard",
                "models": [
                    "M952100",
                    "M961854",
                    "A954440",
                    "Ceramic Disc Cartridge",
                    "Pressure Balance Cartridge"
                ]
            }
        ]
    }
}


def ensure_catalog():
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    if not PRODUCT_OPTIONS_FILE.exists():
        with PRODUCT_OPTIONS_FILE.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_PRODUCT_OPTIONS, f, indent=2)


def load_product_options():
    ensure_catalog()

    with PRODUCT_OPTIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def singularize(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"

    if word.endswith("s") and len(word) > 3:
        return word[:-1]

    return word


def build_variations(text: str):
    normalized = normalize_text(text)

    words = normalized.split()

    variations = {
        normalized,
        " ".join(singularize(w) for w in words)
    }

    return variations


def get_product_options_for_query(query: str):
    catalog = load_product_options()

    query_variations = build_variations(query)

    for category, data in catalog.items():
        keywords = data.get("keywords", [])

        for keyword in keywords:
            keyword_variations = build_variations(keyword)

            for qv in query_variations:
                for kv in keyword_variations:

                    if kv in qv or qv in kv:
                        return {
                            "category": category,
                            "brands": data.get("brands", [])
                        }

    return {
        "category": "generic",
        "brands": []
    }


def query_has_known_brand_and_model(query: str) -> bool:
    catalog = load_product_options()
    q = query.lower()

    for data in catalog.values():
        for brand_entry in data.get("brands", []):
            brand = brand_entry.get("brand", "")

            if brand.lower() not in q:
                continue

            for model in brand_entry.get("models", []):
                if model.lower() in q:
                    return True

    return False
