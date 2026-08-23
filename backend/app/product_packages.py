import json
import time
from pathlib import Path

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify

try:
    from app.metadata_repository import metadata_repository
except ImportError:
    from metadata_repository import metadata_repository


CATALOG_DIR = BASE_DIR / "catalog"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def category_slug(category: str) -> str:
    value = (category or "toilets").strip().lower()
    if value in {"toilet", "toilets"}:
        return "toilets"
    return slugify(value)


def product_package_root(category: str, brand: str, model: str) -> Path:
    return CATALOG_DIR / category_slug(category) / slugify(brand) / slugify(model)


def generic_family_for_category(category: str) -> str:
    value = category_slug(category)
    family_map = {
        "toilets": "replace toilet",
        "faucets": "replace kitchen faucet",
        "dishwashers": "install dishwasher",
        "water-heaters": "install water heater",
        "tile": "install tile",
        "siding": "install siding",
    }
    return family_map.get(value, f"install {value.replace('-', ' ')}")


def build_product_package_manifest(
    category: str,
    brand: str,
    model: str,
    product: dict | None = None,
    discovery: dict | None = None,
    overlays: list | None = None,
) -> dict:
    product = product or {}
    discovery = discovery or {}
    overlays = overlays or []

    return {
        "schema_version": 1,
        "package_type": "product_specific_overlay",
        "category": category or product.get("category", ""),
        "brand": brand or product.get("brand", ""),
        "model": model or product.get("model", ""),
        "generic_family": generic_family_for_category(category or product.get("category", "")),
        "compatible_walkthrough_ids": [
            slugify(generic_family_for_category(category or product.get("category", "")))
        ],
        "review_status": product.get("review_status", "draft"),
        "quality_status": product.get("quality_status", "unvalidated"),
        "confidence": product.get("confidence", "UNKNOWN"),
        "product_page_url": product.get("product_page_url", discovery.get("product_page_url", "")),
        "photo_url": product.get("photo_url", ""),
        "remote_photo_url": product.get("remote_photo_url", ""),
        "manual_url": product.get("manual_url", ""),
        "remote_manual_url": product.get("remote_manual_url", ""),
        "overlay_count": len(overlays),
        "asset_status": {
            "photo": "cached" if product.get("photo_url") else "missing",
            "manual": "cached" if product.get("manual_url") else "missing",
            "overlays": "built" if overlays else "missing",
        },
        "updated_at": now_iso(),
    }


def save_product_package_manifest(
    category: str,
    brand: str,
    model: str,
    product: dict | None = None,
    discovery: dict | None = None,
    overlays: list | None = None,
) -> dict:
    root = product_package_root(category, brand, model)
    root.mkdir(parents=True, exist_ok=True)
    manifest = build_product_package_manifest(category, brand, model, product, discovery, overlays)
    (root / "package-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    metadata_repository.upsert_record(
        "product_packages",
        f"{category_slug(category)}:{slugify(brand)}:{slugify(model)}",
        manifest,
    )
    return manifest
