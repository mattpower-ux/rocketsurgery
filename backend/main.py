from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import json

try:
    from app.canonical_images import (
        CANONICAL_IMAGE_DIR,
        canonical_image_status
    )
except ImportError:
    from canonical_images import (
        CANONICAL_IMAGE_DIR,
        canonical_image_status
    )

try:
    from app.storage import (
        load_walkthrough,
        save_walkthrough,
        load_walkthrough_by_id,
        list_walkthrough_manifests,
        slugify
    )
except ImportError:
    from storage import (
        load_walkthrough,
        save_walkthrough,
        load_walkthrough_by_id,
        list_walkthrough_manifests,
        slugify
    )

try:
    from app.generator import generate_placeholder_walkthrough
except ImportError:
    from generator import generate_placeholder_walkthrough

try:
    from app.catalog import (
        get_product_options_for_query,
        query_has_known_brand_and_model
    )
except ImportError:
    from catalog import (
        get_product_options_for_query,
        query_has_known_brand_and_model
    )

try:
    from app.manuals import (
        manual_storage_status,
        save_uploaded_manual
    )
except ImportError:
    from manuals import (
        manual_storage_status,
        save_uploaded_manual
    )

try:
    from app.manual_parser import extract_installation_specs
except ImportError:
    from manual_parser import extract_installation_specs

try:
    from app.spec_walkthrough_builder import build_walkthrough_from_specs
except ImportError:
    from spec_walkthrough_builder import build_walkthrough_from_specs

try:
    from app.spec_overlay import build_spec_overlay
except ImportError:
    from spec_overlay import build_spec_overlay

try:
    from app.model_discovery import process_model_discovery
except ImportError:
    from model_discovery import process_model_discovery

try:
    from app.canonical import seed_canonical_walkthroughs
except ImportError:
    from canonical import seed_canonical_walkthroughs

try:
    from app.admin import (
        admin_status,
        save_bulk_queries,
        save_catalog_request,
        process_bulk_queries,
        save_bulk_catalog_requests,
        list_bulk_query_jobs,
        retry_bulk_query,
        ignore_bulk_query,
        delete_bulk_query,
        retry_and_run_bulk_query,
        process_specific_bulk_query,
        run_next_bulk_queries
    )
except ImportError:
    from admin import (
        admin_status,
        save_bulk_queries,
        save_catalog_request,
        process_bulk_queries,
        save_bulk_catalog_requests,
        list_bulk_query_jobs,
        retry_bulk_query,
        ignore_bulk_query,
        delete_bulk_query,
        retry_and_run_bulk_query,
        process_specific_bulk_query,
        run_next_bulk_queries
    )

try:
    from app.image_registry import (
        build_image_registry,
        load_image_registry
    )
except ImportError:
    from image_registry import (
        build_image_registry,
        load_image_registry
    )

try:
    from app.image_promotion import promote_image_to_canonical
except ImportError:
    from image_promotion import promote_image_to_canonical

try:
    from app.build_status import get_build_status
except ImportError:
    from build_status import get_build_status

try:
    from app.query_logger import log_query_event
except ImportError:
    from query_logger import log_query_event

try:
    from app.image_generator import generate_step_image
except ImportError:
    from image_generator import generate_step_image

import time
import re
import urllib.request
from urllib.parse import urlparse, urljoin
from fastapi import Request
from html import unescape


app = FastAPI(title="RocketSurgery API")

Path("/data/rocketsurgery/images").mkdir(parents=True, exist_ok=True)
CATALOG_IMAGES_DIR = Path("/data/rocketsurgery/catalog-images")
CATALOG_MANUALS_DIR = Path("/data/rocketsurgery/catalog-manuals")
CATALOG_PACKAGES_DIR = Path("/data/rocketsurgery/catalog-packages")
BASE_CATALOG_DIR = Path("/data/rocketsurgery/catalog")
CATALOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_MANUALS_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
BASE_CATALOG_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static/images",
    StaticFiles(directory="/data/rocketsurgery/images"),
    name="images"
)

app.mount(
    "/static/catalog-images",
    StaticFiles(directory=str(CATALOG_IMAGES_DIR)),
    name="catalog-images"
)

app.mount(
    "/static/catalog-manuals",
    StaticFiles(directory=str(CATALOG_MANUALS_DIR)),
    name="catalog-manuals"
)

app.mount(
    "/static/catalog-packages",
    StaticFiles(directory=str(CATALOG_PACKAGES_DIR)),
    name="catalog-packages"
)

app.mount(
    "/static/catalog",
    StaticFiles(directory=str(BASE_CATALOG_DIR)),
    name="catalog-root"
)

app.mount(
    "/static/canonical-images",
    StaticFiles(directory=str(CANONICAL_IMAGE_DIR)),
    name="canonical-images"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WalkthroughRequest(BaseModel):
    query: str


class ManualExtractRequest(BaseModel):
    text_path: str


class ManualWalkthroughRequest(BaseModel):
    query: str
    specs: dict


class BulkQueriesRequest(BaseModel):
    raw_text: str


class CatalogEntryRequest(BaseModel):
    brand: str
    category: str
    models_text: str = ""
    discover_top_models: bool = True


class BulkCatalogRequest(BaseModel):
    raw_text: str


class OverlayRequest(BaseModel):
    query: str
    category: str = ""
    brand: str = ""
    model: str = ""
    extracted_specs: dict = {}


class PromoteImageRequest(BaseModel):
    filename: str
    canonical_key: str
    step_number: int


class QuerySlugRequest(BaseModel):
    query_slug: str


class RegenerateStepImageRequest(BaseModel):
    walkthrough_id: str
    step_id: int
    correction: str = ""


class AcceptStepImageRequest(BaseModel):
    walkthrough_id: str
    step_id: int


class RevertStepImageRequest(BaseModel):
    walkthrough_id: str
    step_id: int


class CatalogPipelineRequest(BaseModel):
    brand: str
    model: str
    category: str = "toilet"


class ProductPagePackageRequest(BaseModel):
    brand: str
    model: str
    category: str = "toilet"
    product_page_url: str



def catalog_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return cleaned or "item"




def public_catalog_manual_url(path: Path) -> str:
    try:
        relative = path.relative_to(CATALOG_MANUALS_DIR)
    except ValueError:
        return ""
    return "/static/catalog-manuals/" + str(relative).replace("\\", "/")


def public_catalog_package_url(path: Path) -> str:
    try:
        relative = path.relative_to(CATALOG_PACKAGES_DIR)
    except ValueError:
        return ""
    return "/static/catalog-packages/" + str(relative).replace("\\", "/")


def model_asset_dir(root: Path, brand: str, model: str, category: str = "toilets") -> Path:
    return root / category / catalog_slug(brand) / catalog_slug(model)


def find_existing_cached_manual(brand: str, model: str) -> str:
    candidate = model_asset_dir(CATALOG_MANUALS_DIR, brand, model) / "installation-manual.pdf"
    if candidate.exists() and candidate.stat().st_size > 0:
        return public_catalog_manual_url(candidate)
    return ""


def cache_install_manual(brand: str, model: str, remote_url: str) -> dict:
    existing = find_existing_cached_manual(brand, model)
    if existing:
        return {"status": "cached", "local_url": existing, "error": ""}

    if not remote_url:
        return {"status": "missing_remote_url", "local_url": "", "error": "No manual URL is stored for this model."}

    try:
        request = urllib.request.Request(
            remote_url,
            headers={
                "User-Agent": "Mozilla/5.0 RocketSurgeryCatalogBot/1.0",
                "Accept": "application/pdf,*/*;q=0.8",
            }
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(20_000_000)

        if not data or len(data) < 1024:
            raise ValueError("Downloaded manual was empty or too small.")

        if "pdf" not in (content_type or "").lower() and not remote_url.lower().endswith(".pdf"):
            raise ValueError(f"Manual URL did not return a PDF. Content-Type: {content_type}")

        output_dir = model_asset_dir(CATALOG_MANUALS_DIR, brand, model)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "installation-manual.pdf"
        output_path.write_bytes(data)
        return {"status": "downloaded", "local_url": public_catalog_manual_url(output_path), "error": ""}
    except Exception as exc:
        return {"status": "unavailable", "local_url": "", "error": str(exc)}


def overlay_package_path(brand: str, model: str) -> Path:
    return model_asset_dir(CATALOG_PACKAGES_DIR, brand, model) / "overlays.json"


def save_overlay_package(brand: str, model: str, overlay_payload: dict) -> dict:
    path = overlay_package_path(brand, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    package = {
        "category": "toilet",
        "brand": brand,
        "model": model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manual_url": overlay_payload.get("manual_url", ""),
        "local_manual_url": overlay_payload.get("local_manual_url", ""),
        "product_image_url": overlay_payload.get("product_image_url", ""),
        "product_page_url": overlay_payload.get("product_page_url", ""),
        "installation_tips": overlay_payload.get("installation_tips", []),
        "overlays": overlay_payload.get("overlays", []),
    }
    path.write_text(json.dumps(package, indent=2), encoding="utf-8")
    return {"status": "saved", "package_url": public_catalog_package_url(path), "package_path": str(path), "package": package}


def load_overlay_package(brand: str, model: str) -> dict | None:
    path = overlay_package_path(brand, model)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_product_page_product(category: str, brand: str, model: str) -> dict | None:
    """Load a Catalog Intelligence v2 product.json package if it exists.

    Product packages are stored independently from walkthroughs and can be
    reused by any compatible walkthrough in the same category.
    """
    path = product_package_root(category or "toilet", brand, model) / "product.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def package_asset_or_blank(product: dict | None, key: str) -> str:
    if not product:
        return ""
    value = product.get(key, "")
    return value if isinstance(value, str) else ""


def get_toilet_catalog_pipeline_status(brand: str, model: str) -> dict:
    manual = find_toilet_manual(brand, model)
    local_image = find_existing_cached_product_image(brand, model)
    local_manual = find_existing_cached_manual(brand, model)
    package = load_overlay_package(brand, model)
    return {
        "brand": brand,
        "model": model,
        "category": "toilet",
        "photo": {
            "status": "cached" if local_image else "missing",
            "local_url": local_image,
            "remote_url": (manual or {}).get("product_image_url", ""),
            "product_page_url": (manual or {}).get("product_page_url", ""),
        },
        "manual": {
            "status": "cached" if local_manual else ("remote_available" if (manual or {}).get("manual_url") else "missing"),
            "local_url": local_manual,
            "remote_url": (manual or {}).get("manual_url", ""),
            "title": (manual or {}).get("manual_title", ""),
        },
        "overlay": {
            "status": "built" if package else "not_built",
            "tip_count": len((package or {}).get("installation_tips", [])),
            "hotspot_count": len((package or {}).get("overlays", [])),
            "package_url": public_catalog_package_url(overlay_package_path(brand, model)) if package else "",
        },
        "confidence": "HIGH" if local_image and local_manual and package else ("MEDIUM" if local_manual and package else "LOW"),
    }

def content_type_extension(content_type: str, fallback_url: str = "") -> str:
    ct = (content_type or "").lower().split(";", 1)[0].strip()
    if ct in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if ct == "image/png":
        return ".png"
    if ct == "image/webp":
        return ".webp"
    suffix = Path(urlparse(fallback_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def public_catalog_image_url(path: Path) -> str:
    try:
        relative = path.relative_to(CATALOG_IMAGES_DIR)
    except ValueError:
        return ""
    return "/static/catalog-images/" + str(relative).replace("\\", "/")


def find_existing_cached_product_image(brand: str, model: str) -> str:
    base_dir = CATALOG_IMAGES_DIR / "toilets" / catalog_slug(brand)
    stem = catalog_slug(model)
    for ext in [".jpg", ".png", ".webp"]:
        candidate = base_dir / f"{stem}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            return public_catalog_image_url(candidate)
    return ""


def cache_product_image(brand: str, model: str, remote_url: str) -> dict:
    """Cache manufacturer product images on the Render disk.

    Manufacturer image hotlinks are often blocked in the browser. This downloads
    once from the backend and returns a local /static/catalog-images/... URL.
    """
    existing = find_existing_cached_product_image(brand, model)
    if existing:
        return {"status": "cached", "local_url": existing, "error": ""}

    if not remote_url:
        return {
            "status": "missing_remote_url",
            "local_url": "",
            "error": "No remote product image URL is stored for this model."
        }

    try:
        request = urllib.request.Request(
            remote_url,
            headers={
                "User-Agent": "Mozilla/5.0 RocketSurgeryCatalogBot/1.0",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(8_000_000)

        if not data or len(data) < 256:
            raise ValueError("Downloaded image was empty or too small.")

        ext = content_type_extension(content_type, remote_url)
        output_path = CATALOG_IMAGES_DIR / "toilets" / catalog_slug(brand) / f"{catalog_slug(model)}{ext}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)

        return {"status": "downloaded", "local_url": public_catalog_image_url(output_path), "error": ""}
    except Exception as exc:
        return {"status": "unavailable", "local_url": "", "error": str(exc)}


TOILET_PRODUCT_CATALOG = {
    "Kohler": {
        "Highline": {
            "manual_title": "Kohler Highline / Wellworth Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/1004604_2.pdf",
            "product_image_url": "https://www.kohler.com/content/dam/kohler-com-NA/Lifestyle/ProductImages/Toilets/highline-toilet.jpg",
            "product_page_url": "https://www.kohler.com/en/products/toilets/shop-toilets/highline",
            "models": ["Highline", "Wellworth", "Cimarron"]
        },
        "Wellworth": {
            "manual_title": "Kohler Wellworth / Highline Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/114903_2.pdf",
            "product_image_url": "https://www.kohler.com/content/dam/kohler-com-NA/Lifestyle/ProductImages/Toilets/wellworth-toilet.jpg",
            "product_page_url": "https://www.kohler.com/en/products/toilets/shop-toilets/wellworth",
            "models": ["Highline", "Wellworth", "Cimarron"]
        },
        "Cimarron": {
            "manual_title": "Kohler Toilet Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/1004604_2.pdf",
            "product_image_url": "https://www.kohler.com/content/dam/kohler-com-NA/Lifestyle/ProductImages/Toilets/cimarron-toilet.jpg",
            "product_page_url": "https://www.kohler.com/en/products/toilets/shop-toilets/cimarron",
            "models": ["Highline", "Wellworth", "Cimarron"]
        }
    },
    "Niagara": {
        "Original Stealth": {
            "manual_title": "Niagara Original Stealth Installation Manual",
            "manual_url": "",
            "product_image_url": "",
            "product_page_url": "https://niagaracorp.com/products/original-stealth-handle-round/",
            "models": ["Original Stealth", "Stealth", "EcoLogic", "Liberty"]
        },
        "Stealth": {
            "manual_title": "Niagara Stealth Toilet Manual",
            "manual_url": "https://niagaracorp.com/wp-content/uploads/2016/10/Stealth_Manual_Final.pdf",
            "product_image_url": "",
            "product_page_url": "https://niagaracorp.com/products/original-stealth-handle-round/",
            "models": ["Original Stealth", "Stealth", "EcoLogic", "Liberty"]
        },
        "EcoLogic": {
            "manual_title": "Niagara EcoLogic / Toilet Manual",
            "manual_url": "https://niagaracorp.com/wp-content/uploads/2016/10/Stealth_Manual_Final.pdf",
            "product_image_url": "https://niagaracorp.com/wp-content/uploads/2020/04/EcoLogic-Toilet.png",
            "product_page_url": "https://niagaracorp.com/products/",
            "models": ["Original Stealth", "Stealth", "EcoLogic", "Liberty"]
        },
        "Liberty": {
            "manual_title": "Niagara Product Resources",
            "manual_url": "https://pro.niagaracorp.com/resources/",
            "product_image_url": "https://niagaracorp.com/wp-content/uploads/2020/04/Liberty-Toilet.png",
            "product_page_url": "https://niagaracorp.com/products/",
            "models": ["Original Stealth", "Stealth", "EcoLogic", "Liberty"]
        }
    },
    "American Standard": {
        "Cadet 3": {
            "manual_title": "American Standard Cadet Installation Instructions",
            "manual_url": "https://lixil.cdn.celum.cloud/167930_as_us_bath_install__2467__2876%20%284626%29_0_original.pdf",
            "product_image_url": "https://www.americanstandard-us.com/-/media/sites/asus/images/products/toilets/cadet-3-toilet.png",
            "product_page_url": "https://www.americanstandard-us.com/bathroom/toilets",
            "models": ["Cadet 3", "Champion 4", "Colony"]
        },
        "Champion 4": {
            "manual_title": "American Standard Champion / Toilet Installation Instructions",
            "manual_url": "https://s1.img-b.com/build.com/mediabase/specifications/american_standard/1237308/american-standard-2886.518-b-installation-sheet.pdf",
            "product_image_url": "https://www.americanstandard-us.com/-/media/sites/asus/images/products/toilets/champion-4-toilet.png",
            "product_page_url": "https://www.americanstandard-us.com/bathroom/toilets",
            "models": ["Cadet 3", "Champion 4", "Colony"]
        },
        "Colony": {
            "manual_title": "American Standard Toilet Installation Instructions",
            "manual_url": "https://lixil.cdn.celum.cloud/167930_as_us_bath_install__2467__2876%20%284626%29_0_original.pdf",
            "product_image_url": "https://www.americanstandard-us.com/-/media/sites/asus/images/products/toilets/colony-toilet.png",
            "product_page_url": "https://www.americanstandard-us.com/bathroom/toilets",
            "models": ["Cadet 3", "Champion 4", "Colony"]
        }
    }
}


def is_toilet_query(query: str) -> bool:
    q = (query or "").lower()
    return "toilet" in q or "commode" in q or "water closet" in q


def toilet_product_options(query: str):
    return {
        "query": query,
        "category": "toilet",
        "brands": [
            {
                "brand": brand,
                "models": list(next(iter(models.values())).get("models", models.keys()))
            }
            for brand, models in TOILET_PRODUCT_CATALOG.items()
        ],
        "query_has_known_brand_and_model": False
    }


def find_toilet_manual(brand: str, model: str):
    brand_records = TOILET_PRODUCT_CATALOG.get((brand or "").strip())
    if not brand_records:
        return None
    if model in brand_records:
        return brand_records[model]
    model_l = (model or "").lower()
    for model_name, record in brand_records.items():
        if model_l and (model_l in model_name.lower() or model_name.lower() in model_l):
            return record
    return next(iter(brand_records.values()))


def toilet_model_overlay(request: OverlayRequest):
    brand = (request.brand or "").strip()
    model = (request.model or "").strip()
    manual = find_toilet_manual(brand, model)
    if not brand or not manual:
        return {
            "status": "no_model_overlay",
            "category": "toilet",
            "brand": brand,
            "model": model,
            "manual_url": "",
            "product_image_url": "",
            "local_product_image_url": "",
            "remote_product_image_url": "",
            "product_image_status": "missing",
            "product_image_error": "",
            "product_page_url": "",
            "installation_tips": [],
            "overlays": []
        }

    v2_product = load_product_page_product("toilet", brand, model)

    if v2_product:
        image_cache = {
            "status": "cached" if v2_product.get("photo_url") else "missing",
            "local_url": v2_product.get("photo_url", ""),
            "error": "" if v2_product.get("photo_url") else "No cached photo in product package."
        }
        local_manual_url = v2_product.get("manual_url", "")
    else:
        image_cache = cache_product_image(brand, model, manual.get("product_image_url", ""))
        local_manual_url = find_existing_cached_manual(brand, model)

    overlays = [
        {
            "id": "rough-in-check",
            "step_id": 1,
            "x": 58,
            "y": 42,
            "label": "Rough-in",
            "title": "Verify model rough-in before setting the bowl",
            "content": "Before setting the toilet, confirm the model's rough-in and flange/bolt position against the manufacturer guide. Some models offer 10-inch or 12-inch rough-in variants, and a generic walkthrough may not flag that difference.",
            "type": "model_specific",
        },
        {
            "id": "tightening-caution",
            "step_id": 4,
            "x": 52,
            "y": 50,
            "label": "Caution",
            "title": "Tightening sequence and china protection",
            "content": "Use the model-specific tightening sequence and avoid overtightening tank, bowl, seat, or floor fasteners. Vitreous china can crack if hardware is tightened beyond the manufacturer's instructions.",
            "type": "caution",
        },
        {
            "id": "water-level-adjustment",
            "step_id": 6,
            "x": 62,
            "y": 42,
            "label": "Water level",
            "title": "Adjust water level to the model marking",
            "content": "After connecting the supply and test-flushing, adjust the tank water level to the model's marked waterline or valve instructions rather than relying only on generic fill-valve guidance.",
            "type": "adjustment",
        }
    ]

    brand_l = brand.lower()
    model_l = model.lower()
    if "niagara" in brand_l or "stealth" in model_l:
        overlays.append({
            "id": "niagara-stealth-components",
            "step_id": 6,
            "x": 42,
            "y": 36,
            "label": "Tank system",
            "title": "Niagara uses model-specific tank components",
            "content": "Niagara Stealth-style toilets use specialized internal tank components. Do not treat internal adjustments as generic flapper-only adjustments; follow the Niagara manual before changing the flush or fill assembly.",
            "type": "model_specific",
        })
    if "american standard" in brand_l or "cadet" in model_l or "champion" in model_l:
        overlays.append({
            "id": "american-standard-ez-install",
            "step_id": 3,
            "x": 50,
            "y": 58,
            "label": "Hardware",
            "title": "Use the included mounting hardware sequence",
            "content": "American Standard Cadet/Champion installations may include model-specific EZ-Install hardware. Follow the packaged bolt, gasket, washer, and knob sequence instead of substituting a generic tank-to-bowl order.",
            "type": "model_specific",
        })
    if "kohler" in brand_l:
        overlays.append({
            "id": "kohler-leak-check",
            "step_id": 7,
            "x": 64,
            "y": 52,
            "label": "Leak check",
            "title": "Check connections again after several flushes",
            "content": "Kohler installation guides emphasize flushing several times, checking all connections for leaks, and periodically rechecking after installation. Add this follow-up to the generic completion step.",
            "type": "check",
        })

    for item in overlays:
        item["manual_url"] = manual.get("manual_url", "")
        item["manual_title"] = manual.get("manual_title", "Manufacturer installation guide")

    return {
        "status": "loaded",
        "category": "toilet",
        "brand": brand,
        "model": model,
        "manual_title": manual.get("manual_title", "Manufacturer installation guide"),
        "manual_url": local_manual_url or manual.get("manual_url", ""),
        "local_manual_url": local_manual_url,
        "product_image_url": image_cache.get("local_url", ""),
        "local_product_image_url": image_cache.get("local_url", ""),
        "remote_product_image_url": (v2_product or {}).get("remote_photo_url", "") or manual.get("product_image_url", ""),
        "product_image_status": image_cache.get("status", ""),
        "product_image_error": image_cache.get("error", ""),
        "product_page_url": (v2_product or {}).get("product_page_url", "") or manual.get("product_page_url", ""),
        "installation_tips": overlays,
        "overlays": overlays
    }


DEMO_WALKTHROUGH_ID = "james-hardie-lap-siding-nailing-schedule"

DEMO_WALKTHROUGH = {
    "walkthrough_id": DEMO_WALKTHROUGH_ID,
    "title": "CACHED MANIFEST: James Hardie Lap Siding Nailing Schedule",
    "disclaimer": "Manufacturer guidance only. Local codes and AHJ requirements may vary.",
    "steps": [
        {
            "id": 1,
            "instruction": "Find the wall studs before fastening the siding.",
            "detail": "Fasteners should penetrate framing or approved structural sheathing.",
            "imageLabel": "Step 1: Locate studs",
            "imageUrl": "https://rocketsurgery-api.onrender.com/static/images/test-step.svg",
            "hotspots": [
                {
                    "id": "studs",
                    "label": "Stud spacing",
                    "title": "Stud Spacing",
                    "content": "Common framing is 16 inches on center, but verify the wall."
                }
            ]
        },
        {
            "id": 2,
            "instruction": "Place the siding board in position with the proper overlap.",
            "detail": "Keep laps consistent and follow the product-specific exposure limits.",
            "imageLabel": "Step 2: Set board overlap",
            "imageUrl": "https://rocketsurgery-api.onrender.com/static/images/test-step.svg",
            "hotspots": [
                {
                    "id": "overlap",
                    "label": "Overlap",
                    "title": "Lap / Exposure",
                    "content": "Confirm overlap and exposure from the current product manual."
                }
            ]
        },
        {
            "id": 3,
            "instruction": "Fasten near the top edge according to the manufacturer guide.",
            "detail": "Use corrosion-resistant fasteners suitable for fiber-cement siding.",
            "imageLabel": "Step 3: Nail placement",
            "imageUrl": "https://rocketsurgery-api.onrender.com/static/images/test-step.svg",
            "hotspots": [
                {
                    "id": "nail",
                    "label": "Nail spec",
                    "title": "Fastener Spec",
                    "content": "Use manufacturer-approved corrosion-resistant siding nails. Exact length and type must be verified from the current James Hardie manual."
                }
            ]
        }
    ]
}






def catalog_v2_category_slug(category: str) -> str:
    value = (category or "toilets").strip().lower()
    if value in {"toilet", "toilets"}:
        return "toilets"
    return catalog_slug(value)


def product_package_root(category: str, brand: str, model: str) -> Path:
    return BASE_CATALOG_DIR / catalog_v2_category_slug(category) / catalog_slug(brand) / catalog_slug(model)


def public_catalog_file_url(path: Path) -> str:
    try:
        relative = path.relative_to(BASE_CATALOG_DIR)
    except ValueError:
        return ""
    return "/static/catalog/" + str(relative).replace("\\", "/")


def fetch_text_url(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 RocketSurgeryCatalogBot/2.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(5_000_000)
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def discover_image_candidates(html: str, base_url: str) -> list[str]:
    candidates = []

    # Prefer OpenGraph/Twitter hero images first.
    for pattern in [
        r'<meta[^>]+property=["\\\']og:image["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']',
        r'<meta[^>]+content=["\\\']([^"\\\']+)["\\\'][^>]+property=["\\\']og:image["\\\']',
        r'<meta[^>]+name=["\\\']twitter:image["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']',
        r'<meta[^>]+content=["\\\']([^"\\\']+)["\\\'][^>]+name=["\\\']twitter:image["\\\']',
    ]:
        for match in re.findall(pattern, html, flags=re.IGNORECASE):
            candidates.append(match)

    # Then scan image tags and srcsets.
    for match in re.findall(r'<img[^>]+(?:src|data-src)=["\\\']([^"\\\']+)["\\\']', html, flags=re.IGNORECASE):
        candidates.append(match)

    for srcset in re.findall(r'(?:srcset|data-srcset)=["\\\']([^"\\\']+)["\\\']', html, flags=re.IGNORECASE):
        for part in srcset.split(','):
            url_part = part.strip().split(' ')[0]
            if url_part:
                candidates.append(url_part)

    clean = []
    seen = set()
    for item in candidates:
        url = unescape(item.strip())
        if not url or url.startswith('data:'):
            continue
        absolute = urljoin(base_url, url)
        lower = absolute.lower()
        if not any(ext in lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            continue
        # Avoid logos/icons when possible.
        bad_terms = ['logo', 'icon', 'favicon', 'sprite', 'placeholder']
        if any(term in lower for term in bad_terms):
            continue
        if absolute not in seen:
            seen.add(absolute)
            clean.append(absolute)
    return clean[:20]


def discover_pdf_candidates(html: str, base_url: str) -> list[dict]:
    candidates = []
    for href, text in re.findall(r'<a[^>]+href=["\\\']([^"\\\']+)["\\\'][^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL):
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', unescape(clean_text)).strip()
        absolute = urljoin(base_url, unescape(href.strip()))
        lower_blob = f"{absolute} {clean_text}".lower()
        if '.pdf' in absolute.lower() or any(term in lower_blob for term in ['installation manual', 'install manual', 'installation guide', 'instructions', 'downloads']):
            candidates.append({"url": absolute, "label": clean_text or Path(urlparse(absolute).path).name or "PDF"})

    # Lightweight de-dupe.
    seen = set()
    result = []
    for item in candidates:
        if item['url'] in seen:
            continue
        seen.add(item['url'])
        result.append(item)
    return result[:20]


def score_image_candidate(url: str, brand: str, model: str, product_page_url: str) -> int:
    score = 0
    lower = url.lower()
    host = urlparse(url).netloc.lower()
    page_host = urlparse(product_page_url).netloc.lower()
    if page_host and (host == page_host or host.endswith('.' + page_host)):
        score += 20
    for term in [brand, model, 'toilet', 'product']:
        term = (term or '').lower().replace(' ', '-')
        if term and term in lower:
            score += 10
    if any(ext in lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        score += 3
    return score


def score_pdf_candidate(item: dict) -> int:
    blob = f"{item.get('url','')} {item.get('label','')}".lower()
    score = 0
    for term, points in [
        ('installation manual', 30),
        ('install manual', 25),
        ('installation guide', 25),
        ('install', 12),
        ('instructions', 12),
        ('.pdf', 10),
        ('spec', 3),
    ]:
        if term in blob:
            score += points
    return score


def cache_product_image_to_package(category: str, brand: str, model: str, image_url: str) -> dict:
    if not image_url:
        return {"status": "missing", "local_url": "", "remote_url": "", "error": "No candidate image URL discovered."}
    try:
        request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 RocketSurgeryCatalogBot/2.0",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": image_url,
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(10_000_000)
        if not data or len(data) < 256:
            raise ValueError("Downloaded image was empty or too small.")
        ext = content_type_extension(content_type, image_url)
        out_dir = product_package_root(category, brand, model) / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"hero{ext}"
        out_path.write_bytes(data)
        return {"status": "cached", "local_url": public_catalog_file_url(out_path), "remote_url": image_url, "error": ""}
    except Exception as exc:
        return {"status": "unavailable", "local_url": "", "remote_url": image_url, "error": str(exc)}


def cache_manual_to_package(category: str, brand: str, model: str, manual_url: str) -> dict:
    if not manual_url:
        return {"status": "missing", "local_url": "", "remote_url": "", "error": "No candidate manual URL discovered."}
    try:
        request = urllib.request.Request(
            manual_url,
            headers={
                "User-Agent": "Mozilla/5.0 RocketSurgeryCatalogBot/2.0",
                "Accept": "application/pdf,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(30_000_000)
        if not data or len(data) < 1024:
            raise ValueError("Downloaded manual was empty or too small.")
        if "pdf" not in (content_type or "").lower() and not manual_url.lower().split('?', 1)[0].endswith('.pdf'):
            raise ValueError(f"Manual candidate did not return a PDF. Content-Type: {content_type}")
        out_dir = product_package_root(category, brand, model) / "manuals"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "installation-manual.pdf"
        out_path.write_bytes(data)
        return {"status": "cached", "local_url": public_catalog_file_url(out_path), "remote_url": manual_url, "error": ""}
    except Exception as exc:
        return {"status": "unavailable", "local_url": "", "remote_url": manual_url, "error": str(exc)}


def build_product_page_package(category: str, brand: str, model: str, product_page_url: str) -> dict:
    category = category or "toilet"
    root = product_package_root(category, brand, model)
    root.mkdir(parents=True, exist_ok=True)

    discovery = {
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product_page_url,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "images": [],
        "pdfs": [],
        "photo": {"status": "missing", "local_url": "", "remote_url": "", "error": ""},
        "manual": {"status": "missing", "local_url": "", "remote_url": "", "error": ""},
    }

    try:
        html = fetch_text_url(product_page_url)
        images = discover_image_candidates(html, product_page_url)
        pdfs = discover_pdf_candidates(html, product_page_url)
        images = sorted(images, key=lambda u: score_image_candidate(u, brand, model, product_page_url), reverse=True)
        pdfs = sorted(pdfs, key=score_pdf_candidate, reverse=True)
        discovery["images"] = images
        discovery["pdfs"] = pdfs

        photo = cache_product_image_to_package(category, brand, model, images[0] if images else "")
        manual = cache_manual_to_package(category, brand, model, pdfs[0]["url"] if pdfs else "")
        discovery["photo"] = photo
        discovery["manual"] = manual
        discovery["status"] = "complete" if photo.get("local_url") or manual.get("local_url") else "discovered_no_assets_cached"
    except Exception as exc:
        discovery["status"] = "failed"
        discovery["error"] = str(exc)

    product = {
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product_page_url,
        "photo_url": discovery.get("photo", {}).get("local_url", ""),
        "manual_url": discovery.get("manual", {}).get("local_url", ""),
        "remote_photo_url": discovery.get("photo", {}).get("remote_url", ""),
        "remote_manual_url": discovery.get("manual", {}).get("remote_url", ""),
        "confidence": "HIGH" if discovery.get("photo", {}).get("local_url") and discovery.get("manual", {}).get("local_url") else ("MEDIUM" if discovery.get("photo", {}).get("local_url") or discovery.get("manual", {}).get("local_url") else "LOW"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    (root / "discovery.json").write_text(json.dumps(discovery, indent=2), encoding="utf-8")
    (root / "product.json").write_text(json.dumps(product, indent=2), encoding="utf-8")

    # Phase 1 also writes a starter overlay package so the selected model can
    # immediately drive model-specific briefing tips and hotspot popouts. Later
    # versions will replace this with AI-assisted PDF comparison + admin approval.
    overlay_payload = toilet_model_overlay(
        OverlayRequest(query="install a toilet", category="toilet", brand=brand, model=model)
    )
    (root / "overlays.json").write_text(json.dumps({
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product_page_url,
        "installation_tips": overlay_payload.get("installation_tips", []),
        "overlays": overlay_payload.get("overlays", []),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2), encoding="utf-8")

    return {
        "status": discovery.get("status", "unknown"),
        "product": product,
        "discovery": discovery,
        "product_json_url": public_catalog_file_url(root / "product.json"),
        "discovery_json_url": public_catalog_file_url(root / "discovery.json"),
        "overlays_json_url": public_catalog_file_url(root / "overlays.json"),
    }


@app.post("/admin/catalog/build-product-page-package")
def post_catalog_build_product_page_package(request: ProductPagePackageRequest):
    return build_product_page_package(
        category=request.category,
        brand=request.brand,
        model=request.model,
        product_page_url=request.product_page_url,
    )


@app.get("/catalog/products")
def get_catalog_products(category: str = "toilet"):
    """Return product packages compatible with a category/walkthrough family.

    This is the bridge between generic walkthroughs and product packages.
    The walkthrough asks for category=toilet and receives all toilet models
    that have either starter catalog records or built v2 product packages.
    """
    products = []

    if catalog_v2_category_slug(category) == "toilets":
        for brand, models in TOILET_PRODUCT_CATALOG.items():
            for model, record in models.items():
                v2_product = load_product_page_product("toilet", brand, model)
                products.append({
                    "brand": brand,
                    "model": model,
                    "category": "toilet",
                    "product_page_url": (v2_product or {}).get("product_page_url", "") or record.get("product_page_url", ""),
                    "photo_url": (v2_product or {}).get("photo_url", ""),
                    "manual_url": (v2_product or {}).get("manual_url", "") or find_existing_cached_manual(brand, model) or record.get("manual_url", ""),
                    "confidence": (v2_product or {}).get("confidence", "STARTER"),
                    "source": "product_package" if v2_product else "starter_catalog",
                    "compatible_walkthroughs": ["install-toilet", "replace-toilet"]
                })

    return {"status": "loaded", "category": category, "products": products}

@app.get("/admin/catalog/toilet-status")
def get_catalog_toilet_status():
    items = []
    for brand, models in TOILET_PRODUCT_CATALOG.items():
        for model in models.keys():
            items.append(get_toilet_catalog_pipeline_status(brand, model))
    return {"status": "loaded", "items": items}


@app.post("/admin/catalog/fetch-product-photo")
def post_catalog_fetch_product_photo(request: CatalogPipelineRequest):
    manual = find_toilet_manual(request.brand, request.model)
    if not manual:
        return {"status": "not_found", "brand": request.brand, "model": request.model}
    result = cache_product_image(request.brand, request.model, manual.get("product_image_url", ""))
    return {"status": result.get("status"), "brand": request.brand, "model": request.model, "photo": result, "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model)}


@app.post("/admin/catalog/fetch-install-manual")
def post_catalog_fetch_install_manual(request: CatalogPipelineRequest):
    manual = find_toilet_manual(request.brand, request.model)
    if not manual:
        return {"status": "not_found", "brand": request.brand, "model": request.model}
    result = cache_install_manual(request.brand, request.model, manual.get("manual_url", ""))
    return {"status": result.get("status"), "brand": request.brand, "model": request.model, "manual": result, "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model)}


@app.post("/admin/catalog/build-overlay-package")
def post_catalog_build_overlay_package(request: CatalogPipelineRequest):
    payload = toilet_model_overlay(OverlayRequest(query="install a toilet", category="toilet", brand=request.brand, model=request.model))
    manual_cache = cache_install_manual(request.brand, request.model, payload.get("manual_url", ""))
    if manual_cache.get("local_url"):
        payload["local_manual_url"] = manual_cache.get("local_url")
    saved = save_overlay_package(request.brand, request.model, payload)
    return {"status": "built", "brand": request.brand, "model": request.model, "overlay_package": saved, "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model)}


@app.post("/admin/catalog/run-model-pipelines")
def post_catalog_run_model_pipelines(request: CatalogPipelineRequest):
    manual = find_toilet_manual(request.brand, request.model)
    if not manual:
        return {"status": "not_found", "brand": request.brand, "model": request.model}
    photo_result = cache_product_image(request.brand, request.model, manual.get("product_image_url", ""))
    manual_result = cache_install_manual(request.brand, request.model, manual.get("manual_url", ""))
    payload = toilet_model_overlay(OverlayRequest(query="install a toilet", category="toilet", brand=request.brand, model=request.model))
    if manual_result.get("local_url"):
        payload["local_manual_url"] = manual_result.get("local_url")
    saved = save_overlay_package(request.brand, request.model, payload)
    return {
        "status": "complete",
        "brand": request.brand,
        "model": request.model,
        "photo": photo_result,
        "manual": manual_result,
        "overlay_package": saved,
        "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model),
    }


@app.get("/")
def root():
    return {"status": "RocketSurgery API is running"}


@app.get("/seed-demo")
def seed_demo():
    save_walkthrough(DEMO_WALKTHROUGH_ID, DEMO_WALKTHROUGH)

    return {
        "status": "saved",
        "walkthrough_id": DEMO_WALKTHROUGH_ID
    }


@app.get("/product-options")
def product_options(query: str):
    if is_toilet_query(query):
        return toilet_product_options(query)

    options = get_product_options_for_query(query)

    return {
        "query": query,
        "category": options.get("category", "generic"),
        "brands": options.get("brands", []),
        "query_has_known_brand_and_model":
            query_has_known_brand_and_model(query)
    }


@app.get("/manuals/status")
def manuals_status():
    return manual_storage_status()


@app.post("/manuals/upload")
async def upload_manual(
    manufacturer: str = Form(...),
    file: UploadFile = File(...)
):
    contents = await file.read()

    result = save_uploaded_manual(
        file_bytes=contents,
        filename=file.filename,
        manufacturer=manufacturer
    )

    return result


@app.post("/manuals/extract-specs")
def manuals_extract_specs(request: ManualExtractRequest):
    return extract_installation_specs(request.text_path)


@app.post("/manuals/build-walkthrough")
def manuals_build_walkthrough(request: ManualWalkthroughRequest):
    walkthrough = build_walkthrough_from_specs(
        query=request.query,
        specs=request.specs
    )

    save_walkthrough(walkthrough["walkthrough_id"], walkthrough)

    return walkthrough


@app.get("/admin/status")
def get_admin_status():
    return admin_status()


@app.post("/admin/bulk-queries")
def post_bulk_queries(request: BulkQueriesRequest):
    return save_bulk_queries(request.raw_text)


@app.post("/admin/catalog-entry")
def post_catalog_entry(request: CatalogEntryRequest):
    return save_catalog_request(
        brand=request.brand,
        category=request.category,
        models_text=request.models_text,
        discover_top_models=request.discover_top_models
    )


@app.post("/admin/bulk-catalog")
def post_bulk_catalog(request: BulkCatalogRequest):
    return save_bulk_catalog_requests(request.raw_text)


@app.post("/admin/process-bulk-queries")
def post_process_bulk_queries(limit: int = 5):
    # Manual processing trigger from Admin.
    # This does not start the external Render worker service; it runs queued jobs now.
    return run_next_bulk_queries(limit=limit)


@app.post("/admin/process-model-discovery")
def post_process_model_discovery(limit: int = 5):
    return process_model_discovery(limit=limit)


@app.post("/admin/seed-canonical-walkthroughs")
def post_seed_canonical_walkthroughs():
    return seed_canonical_walkthroughs()


@app.get("/admin/canonical-image-status")
def get_canonical_image_status():
    return canonical_image_status()


@app.get("/admin/image-registry")
def get_image_registry():
    return load_image_registry()


@app.post("/admin/rebuild-image-registry")
def rebuild_image_registry():
    return build_image_registry()


@app.post("/admin/promote-image")
def promote_image(request: PromoteImageRequest):
    return promote_image_to_canonical(
        filename=request.filename,
        canonical_key=request.canonical_key,
        step_number=request.step_number
    )


@app.get("/admin/walkthrough-build-status")
def walkthrough_build_status():
    return get_build_status()


@app.get("/admin/bulk-query-list")
def get_bulk_query_list():
    return list_bulk_query_jobs()


@app.post("/admin/bulk-query-retry")
def post_bulk_query_retry(request: QuerySlugRequest):
    return retry_bulk_query(request.query_slug)


@app.post("/admin/bulk-query-run")
def post_bulk_query_run(request: QuerySlugRequest):
    return process_specific_bulk_query(request.query_slug)


@app.post("/admin/bulk-query-retry-run")
def post_bulk_query_retry_run(request: QuerySlugRequest):
    return retry_and_run_bulk_query(request.query_slug)


@app.post("/admin/bulk-query-ignore")
def post_bulk_query_ignore(request: QuerySlugRequest):
    return ignore_bulk_query(request.query_slug)


@app.post("/admin/bulk-query-delete")
def post_bulk_query_delete(request: QuerySlugRequest):
    return delete_bulk_query(request.query_slug)


@app.get("/admin/walkthroughs")
def get_admin_walkthroughs(limit: int = 250):
    return {
        "status": "loaded",
        "walkthroughs": list_walkthrough_manifests(limit=limit)
    }


@app.get("/admin/walkthroughs/{walkthrough_id}")
def get_admin_walkthrough(walkthrough_id: str):
    manifest = load_walkthrough_by_id(walkthrough_id)

    if not manifest:
        return {"status": "not_found", "walkthrough_id": walkthrough_id}

    return {"status": "loaded", "walkthrough": manifest}


@app.post("/admin/regenerate-step-image")
def post_regenerate_step_image(request: RegenerateStepImageRequest):
    manifest = load_walkthrough_by_id(request.walkthrough_id)

    if not manifest:
        return {"status": "not_found", "walkthrough_id": request.walkthrough_id}

    steps = manifest.get("steps", []) or []
    target = None

    for step in steps:
        if int(step.get("id", 0)) == int(request.step_id):
            target = step
            break

    if not target:
        return {"status": "step_not_found", "step_id": request.step_id}

    original_prompt = target.get("imagePrompt") or f"{manifest.get('title', request.walkthrough_id)} — {target.get('imageLabel', '')}"
    correction = (request.correction or "Create a clearer, more accurate professional construction training illustration.").strip()

    # Keep prompts short and explicitly safe. This reduces false moderation hits
    # and prevents long prompt-derived image filenames in image_generator.py.
    repair_prompt = " ".join((
        f"{original_prompt}. Correction request: {correction}. "
        "Professional residential construction training illustration. "
        "Show realistic materials, accurate tool placement, safe work positioning, no injuries, no weapons, no illegal activity."
    ).split())
    repair_prompt = repair_prompt.replace("house wrap", "weather-resistive wall barrier")
    repair_prompt = repair_prompt.replace("House wrap", "weather-resistive wall barrier")
    repair_prompt = repair_prompt[:420].rstrip(" ,;:-")

    new_image_url = generate_step_image(repair_prompt, int(request.step_id))

    target["imagePrompt"] = original_prompt
    target["pendingImageUrl"] = new_image_url
    target["pendingImagePrompt"] = repair_prompt
    target["pendingCorrection"] = correction

    history = target.setdefault("imageRepairHistory", [])
    history.append({
        "status": "pending",
        "oldImageUrl": target.get("imageUrl", ""),
        "newImageUrl": new_image_url,
        "correctionPrompt": correction,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })

    save_walkthrough(manifest.get("walkthrough_id") or slugify(request.walkthrough_id), manifest)

    return {
        "status": "pending_review",
        "walkthrough_id": manifest.get("walkthrough_id"),
        "step_id": request.step_id,
        "old_image_url": target.get("imageUrl", ""),
        "new_image_url": new_image_url,
        "walkthrough": manifest
    }


@app.post("/admin/accept-step-image")
def post_accept_step_image(request: AcceptStepImageRequest):
    manifest = load_walkthrough_by_id(request.walkthrough_id)

    if not manifest:
        return {"status": "not_found", "walkthrough_id": request.walkthrough_id}

    for step in manifest.get("steps", []) or []:
        if int(step.get("id", 0)) == int(request.step_id):
            pending = step.get("pendingImageUrl")
            if not pending:
                return {"status": "no_pending_image", "step_id": request.step_id}

            previous = step.get("imageUrl", "")
            step["previousImageUrl"] = previous
            step["imageUrl"] = pending
            step["imagePrompt"] = step.get("pendingImagePrompt") or step.get("imagePrompt", "")
            step.pop("pendingImageUrl", None)
            step.pop("pendingImagePrompt", None)
            step.pop("pendingCorrection", None)

            for item in step.get("imageRepairHistory", []):
                if item.get("newImageUrl") == pending and item.get("status") == "pending":
                    item["status"] = "accepted"
                    item["accepted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            save_walkthrough(manifest.get("walkthrough_id") or slugify(request.walkthrough_id), manifest)
            return {"status": "accepted", "walkthrough": manifest}

    return {"status": "step_not_found", "step_id": request.step_id}


@app.post("/admin/revert-step-image")
def post_revert_step_image(request: RevertStepImageRequest):
    manifest = load_walkthrough_by_id(request.walkthrough_id)

    if not manifest:
        return {"status": "not_found", "walkthrough_id": request.walkthrough_id}

    for step in manifest.get("steps", []) or []:
        if int(step.get("id", 0)) == int(request.step_id):
            if step.get("pendingImageUrl"):
                step.pop("pendingImageUrl", None)
                step.pop("pendingImagePrompt", None)
                step.pop("pendingCorrection", None)
                save_walkthrough(manifest.get("walkthrough_id") or slugify(request.walkthrough_id), manifest)
                return {"status": "discarded_pending", "walkthrough": manifest}

            previous = step.get("previousImageUrl")
            if previous:
                current = step.get("imageUrl", "")
                step["imageUrl"] = previous
                step["previousImageUrl"] = current
                save_walkthrough(manifest.get("walkthrough_id") or slugify(request.walkthrough_id), manifest)
                return {"status": "reverted", "walkthrough": manifest}

            return {"status": "nothing_to_revert", "step_id": request.step_id}

    return {"status": "step_not_found", "step_id": request.step_id}


@app.post("/walkthrough/overlay")
def walkthrough_overlay(request: OverlayRequest):
    if request.category == "toilet" or is_toilet_query(request.query):
        return toilet_model_overlay(request)

    return build_spec_overlay(
        query=request.query,
        category=request.category,
        brand=request.brand,
        model=request.model,
        extracted_specs=request.extracted_specs
    )


@app.post("/walkthrough")
def get_walkthrough(
    request: WalkthroughRequest,
    http_request: Request
):
    start_time = time.time()

    cached = load_walkthrough(request.query)

    client_ip = (
        http_request.headers.get("x-forwarded-for")
        or (http_request.client.host if http_request.client else "")
    )

    user_agent = http_request.headers.get("user-agent", "")

    if cached:
        elapsed_ms = int((time.time() - start_time) * 1000)

        try:
            log_query_event(
                query=request.query,
                walkthrough_id=cached.get("walkthrough_id", ""),
                cache_hit=True,
                response_time_ms=elapsed_ms,
                ip_address=client_ip,
                user_agent=user_agent
            )
        except Exception as e:
            print("Query logging failed:", e)

        return cached

    generated = generate_placeholder_walkthrough(request.query)

    save_walkthrough(generated["walkthrough_id"], generated)

    elapsed_ms = int((time.time() - start_time) * 1000)

    try:
        log_query_event(
            query=request.query,
            walkthrough_id=generated.get("walkthrough_id", ""),
            cache_hit=False,
            response_time_ms=elapsed_ms,
            ip_address=client_ip,
            user_agent=user_agent
        )
    except Exception as e:
        print("Query logging failed:", e)

    return generated
