from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pathlib import Path
import json
import csv
import io

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
        BASE_DIR,
        IMAGES_DIR,
        load_walkthrough,
        save_walkthrough,
        delete_walkthrough,
        resolve_walkthrough_storage_id,
        load_walkthrough_by_id,
        list_walkthrough_manifests,
        slugify,
        query_to_walkthrough_id
    )
except ImportError:
    from storage import (
        BASE_DIR,
        IMAGES_DIR,
        load_walkthrough,
        save_walkthrough,
        delete_walkthrough,
        resolve_walkthrough_storage_id,
        load_walkthrough_by_id,
        list_walkthrough_manifests,
        slugify,
        query_to_walkthrough_id
    )

try:
    from app.generator import (
        GENERATOR_SCHEMA_VERSION,
        build_visual_assets,
        build_visual_template,
        format_asset_sheet_brief,
        generate_placeholder_walkthrough,
    )
except ImportError:
    from generator import (
        GENERATOR_SCHEMA_VERSION,
        build_visual_assets,
        build_visual_template,
        format_asset_sheet_brief,
        generate_placeholder_walkthrough,
    )

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
    from app.query_logger import (
        list_visitor_events,
        log_query_event,
        log_visitor_event,
        visitor_events_csv,
    )
except ImportError:
    from query_logger import (
        list_visitor_events,
        log_query_event,
        log_visitor_event,
        visitor_events_csv,
    )

try:
    from app.walkthrough_index import (
        find_approved_duplicate_for_manifest,
        rebuild_walkthrough_index_from_storage,
        taxonomy_integrity_report,
        walkthrough_library,
    )
except ImportError:
    from walkthrough_index import (
        find_approved_duplicate_for_manifest,
        rebuild_walkthrough_index_from_storage,
        taxonomy_integrity_report,
        walkthrough_library,
    )

try:
    from app.taxonomy_router import classify_taxonomy_query
except ImportError:
    from taxonomy_router import classify_taxonomy_query

try:
    from app.taxonomy_edits import record_query_alias_candidate
except ImportError:
    from taxonomy_edits import record_query_alias_candidate

try:
    from app.image_generator import generate_step_image, generate_step_image_from_asset_sheet, generate_visual_asset_sheet
except ImportError:
    from image_generator import generate_step_image, generate_step_image_from_asset_sheet, generate_visual_asset_sheet

try:
    from app.image_quality import assess_and_record_image_quality
except ImportError:
    from image_quality import assess_and_record_image_quality

try:
    from app.training_examples import (
        image_repair_example,
        product_photo_example,
        walkthrough_edit_example,
    )
except ImportError:
    from training_examples import (
        image_repair_example,
        product_photo_example,
        walkthrough_edit_example,
    )

try:
    from app.editor_learning import learn_from_walkthrough_edit
except ImportError:
    from editor_learning import learn_from_walkthrough_edit

try:
    from app.source_research import discover_source_research
except ImportError:
    from source_research import discover_source_research

try:
    from app.product_packages import save_product_package_manifest
except ImportError:
    from product_packages import save_product_package_manifest

import time
import re
import urllib.request
import os
from urllib.parse import urlparse, urljoin
from fastapi import Request
from html import unescape


app = FastAPI(title="RocketSurgery API")

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_IMAGES_DIR = BASE_DIR / "catalog-images"
CATALOG_MANUALS_DIR = BASE_DIR / "catalog-manuals"
CATALOG_PACKAGES_DIR = BASE_DIR / "catalog-packages"
BASE_CATALOG_DIR = BASE_DIR / "catalog"
INTELLIGENCE_DIR = BASE_DIR / "intelligence"
CORRECTION_MEMORY_FILE = INTELLIGENCE_DIR / "correction_memory.jsonl"
EDITOR_DECISIONS_FILE = INTELLIGENCE_DIR / "editor_decisions.jsonl"
CATEGORY_RULES_FILE = INTELLIGENCE_DIR / "category_rules.json"

CATALOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_MANUALS_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
BASE_CATALOG_DIR.mkdir(parents=True, exist_ok=True)
INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static/images",
    StaticFiles(directory=str(IMAGES_DIR)),
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
    force_refresh: bool = False


class VisitorEventRequest(BaseModel):
    event: str = "client_event"
    query: str = ""
    walkthrough_id: str = ""
    path: str = ""
    time_spent_seconds: float = 0
    metadata: dict = Field(default_factory=dict)


class ManualExtractRequest(BaseModel):
    text_path: str


class ManualWalkthroughRequest(BaseModel):
    query: str
    specs: dict


class BulkQueriesRequest(BaseModel):
    raw_text: str


class SourceResearchRequest(BaseModel):
    query: str
    force_refresh: bool = False


class CatalogEntryRequest(BaseModel):
    brand: str
    category: str
    models_text: str = ""
    discover_top_models: bool = True


class BulkCatalogRequest(BaseModel):
    raw_text: str


class QcWalkthroughAction(BaseModel):
    walkthrough_id: str
    action: str
    steps: list[dict] = []
    title: str | None = None
    query: str | None = None
    visual_template: str | None = None


class QcSaveAllRequest(BaseModel):
    actions: list[QcWalkthroughAction]


class SaveWalkthroughRequest(BaseModel):
    walkthrough: dict


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


class GenerateQcStepImageRequest(BaseModel):
    walkthrough_id: str
    title: str = ""
    query: str = ""
    step: dict
    image_direction: str = ""
    visual_template: str = ""
    visual_assets: dict = Field(default_factory=dict)


class RegenerateAllQcImagesRequest(BaseModel):
    walkthrough_id: str
    title: str = ""
    query: str = ""
    steps: list[dict] = Field(default_factory=list)
    visual_template: str = ""
    visual_assets: dict = Field(default_factory=dict)


class QcVisualMigrationRequest(BaseModel):
    limit: int = 5
    review_status: str = "all"
    dry_run: bool = False
    generate_asset_sheets: bool = False
    walkthrough_ids: list[str] = Field(default_factory=list)


class AdoptApprovedMatchRequest(BaseModel):
    walkthrough_id: str
    walkthrough: dict = Field(default_factory=dict)


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


class CatalogPhotoRequest(BaseModel):
    brand: str
    model: str
    category: str = "toilet"
    image_url: str = ""



def catalog_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return cleaned or "item"


def infer_construction_category(walkthrough_id: str = "", title: str = "", query: str = "") -> str:
    """Infer a broad construction category for correction memory records.

    This lightweight mapper is intentionally conservative. It lets the
    intelligence layer group corrections before we have a full taxonomy service.
    """
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
    """Load durable category visual rules from the Render disk."""
    if not CATEGORY_RULES_FILE.exists():
        return {}
    try:
        return json.loads(CATEGORY_RULES_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print("Category rules read failed:", exc)
        return {}


def category_rules_for(category: str) -> dict:
    rules = load_category_rules()
    value = rules.get(category or "generic", {})
    return value if isinstance(value, dict) else {}


def format_rules_for_prompt(category: str) -> str:
    """Format category visual rules for image prompt injection."""
    rules = category_rules_for(category)
    must_show = rules.get("must_show", []) or []
    must_not_show = rules.get("must_not_show", []) or []
    step_order = rules.get("step_order", []) or []
    common_errors = rules.get("common_errors", []) or []
    parts = []
    if step_order:
        parts.append("Preferred step logic: " + "; ".join(str(item) for item in step_order[:10]) + ".")
    if must_show:
        parts.append("Must show: " + "; ".join(str(item) for item in must_show[:8]) + ".")
    if must_not_show:
        parts.append("Must not show: " + "; ".join(str(item) for item in must_not_show[:8]) + ".")
    if common_errors:
        parts.append("Avoid these known errors: " + "; ".join(str(item) for item in common_errors[:8]) + ".")
    return " ".join(parts)


def append_jsonl(path: Path, payload: dict):
    """Append one JSON object per line to a durable Render-disk file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"JSONL append failed for {path}:", exc)


def log_correction_memory(payload: dict):
    """Persist editorial corrections/actions for self-improving walkthroughs."""
    try:
        record = dict(payload or {})
        record.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        append_jsonl(CORRECTION_MEMORY_FILE, record)
    except Exception as exc:
        print("Correction memory write failed:", exc)


def log_editor_decision(payload: dict):
    """Persist editorial decisions separately from raw correction memory."""
    try:
        record = dict(payload or {})
        record.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        append_jsonl(EDITOR_DECISIONS_FILE, record)
    except Exception as exc:
        print("Editor decision write failed:", exc)


IMAGE_PRICE_BY_QUALITY = {
    "low": 0.011,
    "medium": 0.042,
    "high": 0.167,
}


def estimated_image_generation_costs(image_count: int) -> dict:
    count = max(0, int(image_count or 0))
    return {
        quality: round(count * unit_price, 2)
        for quality, unit_price in IMAGE_PRICE_BY_QUALITY.items()
    }


def migration_status_matches(item_status: str, requested_status: str) -> bool:
    status = (item_status or "draft").lower()
    requested = (requested_status or "all").lower()
    if requested == "all":
        return status not in ["deleted", "deprecated"]
    if requested == "draft":
        return status not in ["approved", "deleted", "deprecated"]
    return status == requested


def visual_migration_item_for_manifest(item: dict, manifest: dict) -> dict:
    walkthrough_id = item.get("storage_walkthrough_id") or item.get("walkthrough_id", "")
    query = manifest.get("query") or item.get("title") or walkthrough_id
    category = infer_construction_category(
        walkthrough_id=walkthrough_id,
        title=manifest.get("title", item.get("title", "")),
        query=query,
    )
    steps = manifest.get("steps", []) or []
    visual_assets = manifest.get("visual_assets") or {}
    has_template = bool(str(manifest.get("visual_template") or "").strip())
    has_asset_sheet = bool(str(visual_assets.get("asset_sheet_url") or "").strip())
    image_count = len([step for step in steps if step.get("imageUrl")])
    asset_sheet_calls_needed = 0 if has_asset_sheet else 1
    step_image_calls_needed = len(steps)
    full_regen_calls = asset_sheet_calls_needed + step_image_calls_needed
    readiness = "ready_for_review"
    if not has_template:
        readiness = "needs_visual_template"
    elif not has_asset_sheet:
        readiness = "needs_asset_sheet"

    return {
        "walkthrough_id": walkthrough_id,
        "title": manifest.get("title") or item.get("title") or walkthrough_id,
        "query": query,
        "review_status": manifest.get("review_status", item.get("review_status", "draft")),
        "quality_status": manifest.get("quality_status", item.get("quality_status", "unvalidated")),
        "category": category,
        "step_count": len(steps),
        "existing_image_count": image_count,
        "has_visual_template": has_template,
        "has_asset_sheet": has_asset_sheet,
        "asset_sheet_url": visual_assets.get("asset_sheet_url", ""),
        "asset_sheet_calls_needed": asset_sheet_calls_needed,
        "step_image_calls_needed": step_image_calls_needed,
        "full_regen_calls": full_regen_calls,
        "estimated_full_regen_costs": estimated_image_generation_costs(full_regen_calls),
        "readiness": readiness,
    }


def visual_migration_report(limit: int = 10000, review_status: str = "all") -> dict:
    items = []
    for item in list_walkthrough_manifests(limit=limit):
        if not migration_status_matches(item.get("review_status", "draft"), review_status):
            continue
        walkthrough_id = item.get("storage_walkthrough_id") or item.get("walkthrough_id", "")
        manifest = load_walkthrough_by_id(walkthrough_id)
        if not manifest:
            continue
        items.append(visual_migration_item_for_manifest(item, manifest))

    total_full_regen_calls = sum(item.get("full_regen_calls", 0) for item in items)
    total_asset_sheet_calls = sum(item.get("asset_sheet_calls_needed", 0) for item in items)
    total_step_image_calls = sum(item.get("step_image_calls_needed", 0) for item in items)
    missing_templates = len([item for item in items if not item.get("has_visual_template")])
    missing_asset_sheets = len([item for item in items if not item.get("has_asset_sheet")])

    return {
        "status": "loaded",
        "summary": {
            "walkthrough_count": len(items),
            "missing_visual_template_count": missing_templates,
            "missing_asset_sheet_count": missing_asset_sheets,
            "asset_sheet_calls_needed": total_asset_sheet_calls,
            "step_image_calls_for_full_regen": total_step_image_calls,
            "full_regen_image_calls": total_full_regen_calls,
            "estimated_full_regen_costs": estimated_image_generation_costs(total_full_regen_calls),
            "estimated_asset_sheet_costs": estimated_image_generation_costs(total_asset_sheet_calls),
        },
        "items": items,
    }


def prepare_visual_migration_batch(request: QcVisualMigrationRequest) -> dict:
    target_ids = {resolve_walkthrough_storage_id(item) for item in request.walkthrough_ids or []}
    max_items = max(1, min(int(request.limit or 5), 25))
    candidates = []

    for item in list_walkthrough_manifests(limit=10000):
        walkthrough_id = item.get("storage_walkthrough_id") or item.get("walkthrough_id", "")
        if target_ids and walkthrough_id not in target_ids:
            continue
        if not target_ids and not migration_status_matches(item.get("review_status", "draft"), request.review_status):
            continue
        manifest = load_walkthrough_by_id(walkthrough_id)
        if not manifest:
            continue
        migration_item = visual_migration_item_for_manifest(item, manifest)
        if (
            not migration_item.get("has_visual_template")
            or not migration_item.get("has_asset_sheet")
            or target_ids
        ):
            candidates.append((walkthrough_id, manifest, migration_item))
        if len(candidates) >= max_items:
            break

    prepared = []
    for walkthrough_id, manifest, migration_item in candidates:
        before_manifest = json.loads(json.dumps(manifest))
        query = manifest.get("query") or manifest.get("title") or walkthrough_id
        category = migration_item.get("category", "generic")
        visual_template = str(manifest.get("visual_template") or "").strip()
        if not visual_template:
            visual_template = build_visual_template(query, category)

        visual_assets = dict(manifest.get("visual_assets") or {})
        if not visual_assets:
            visual_assets = build_visual_assets(query, category, visual_template)
        else:
            fallback_assets = build_visual_assets(query, category, visual_template)
            visual_assets = {**fallback_assets, **visual_assets}
            visual_assets["locked_prompt"] = visual_template
            visual_assets["category"] = visual_assets.get("category") or category

        if not visual_assets.get("asset_sheet_url") and category != "chimney_cap":
            visual_assets["asset_key"] = f"walkthrough-{walkthrough_id}"

        visual_assets["asset_sheet_prompt"] = visual_assets.get("asset_sheet_prompt") or format_asset_sheet_brief(visual_assets)

        generated_asset_sheet = False
        if request.generate_asset_sheets and not visual_assets.get("asset_sheet_url"):
            visual_assets["asset_sheet_url"] = generate_visual_asset_sheet(
                visual_assets["asset_sheet_prompt"],
                visual_assets.get("asset_key", f"{category}-asset-sheet"),
            )
            visual_assets["asset_status"] = "generated"
            generated_asset_sheet = True
        elif not visual_assets.get("asset_sheet_url"):
            visual_assets["asset_status"] = visual_assets.get("asset_status") or "template_ready"

        if not request.dry_run:
            manifest["visual_template"] = visual_template
            manifest["visual_assets"] = visual_assets
            manifest["visual_migration_status"] = "asset_sheet_generated" if generated_asset_sheet else "template_prepared"
            manifest["visual_migration_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            manifest["version"] = int(manifest.get("version", 1)) + 1
            save_walkthrough(walkthrough_id, manifest)
            log_editor_decision({
                "action": "qc_visual_migration_prepared",
                "walkthrough_id": walkthrough_id,
                "category": category,
                "generated_asset_sheet": generated_asset_sheet,
                "dry_run": False,
            })

        prepared.append({
            "walkthrough_id": walkthrough_id,
            "title": manifest.get("title") or before_manifest.get("title") or walkthrough_id,
            "category": category,
            "generated_asset_sheet": generated_asset_sheet,
            "dry_run": request.dry_run,
            "has_visual_template": bool(visual_template),
            "has_asset_sheet": bool(visual_assets.get("asset_sheet_url")),
            "asset_sheet_url": visual_assets.get("asset_sheet_url", ""),
        })

    return {
        "status": "prepared" if not request.dry_run else "dry_run",
        "processed_count": len(prepared),
        "generated_asset_sheet_count": len([item for item in prepared if item.get("generated_asset_sheet")]),
        "estimated_asset_sheet_costs": estimated_image_generation_costs(len([item for item in prepared if item.get("generated_asset_sheet")])),
        "items": prepared,
    }


def learn_editor_rules(action: str, before: dict, after: dict, context: dict | None = None):
    try:
        result = learn_from_walkthrough_edit(action, before, after, context or {})
        log_editor_decision({
            "action": "editor_learning_updated",
            "source_action": action,
            "category": result.get("category", ""),
            "walkthrough_id": (after or before or {}).get("walkthrough_id", ""),
            "learned_example_count": (result.get("rules") or {}).get("learned_example_count", 0),
        })
        return result
    except Exception as exc:
        print("Editor learning failed:", exc)
        return {"status": "learning_failed", "error": str(exc)}


def add_manifest_alias(manifest: dict, alias: str):
    value = (alias or "").strip()
    if not value:
        return

    aliases = manifest.setdefault("aliases", [])
    normalized_existing = {
        re.sub(r"\s+", " ", str(item or "").lower()).strip()
        for item in aliases
    }
    normalized_value = re.sub(r"\s+", " ", value.lower()).strip()
    if normalized_value not in normalized_existing:
        aliases.append(value)


def normalize_step_numbering(steps: list[dict]) -> list[dict]:
    normalized_steps = []
    for index, step in enumerate(steps or [], start=1):
        next_step = dict(step or {})
        next_step["id"] = index
        for field in ["imageLabel", "instruction"]:
            value = str(next_step.get(field) or "")
            if re.match(r"^step\s+\d+\s*:", value, flags=re.IGNORECASE):
                next_step[field] = re.sub(
                    r"^step\s+\d+\s*:",
                    f"Step {index}:",
                    value,
                    flags=re.IGNORECASE,
                )
        normalized_steps.append(next_step)
    return normalized_steps


def require_admin_token(x_admin_token: str = Header(default="")):
    expected = os.getenv("ADMIN_API_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_TOKEN is not configured on the API service."
        )
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token.")


def client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else ""


def user_agent_from_request(request: Request) -> str:
    return request.headers.get("user-agent", "")


@app.post("/visitor/event")
def post_visitor_event(payload: VisitorEventRequest, http_request: Request):
    return log_visitor_event(
        event=payload.event,
        query=payload.query,
        walkthrough_id=payload.walkthrough_id,
        path=payload.path,
        time_spent_seconds=payload.time_spent_seconds,
        ip_address=client_ip_from_request(http_request),
        user_agent=user_agent_from_request(http_request),
        metadata=payload.metadata,
    )


@app.get("/admin/visitors")
def get_admin_visitors(
    limit: int = 250,
    start_date: str = "",
    end_date: str = "",
    _: None = Depends(require_admin_token)
):
    return list_visitor_events(
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )


@app.get("/admin/visitors.csv")
def export_admin_visitors_csv(
    start_date: str = "",
    end_date: str = "",
    _: None = Depends(require_admin_token)
):
    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "event",
        "query",
        "walkthrough_id",
        "path",
        "time_spent_seconds",
        "ip_address",
        "user_agent",
        "metadata",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in visitor_events_csv(start_date=start_date, end_date=end_date):
        writer.writerow({field: row.get(field, "") for field in fieldnames})

    filename = "rocketsurgery-visitors"
    if start_date or end_date:
        filename += f"-{start_date or 'begin'}-to-{end_date or 'latest'}"
    filename += ".csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )




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
    """Status for starter catalog records plus Catalog Intelligence v2 packages."""
    manual = find_toilet_manual(brand, model)
    v2_product = load_product_page_product("toilet", brand, model)
    local_image = package_asset_or_blank(v2_product, "photo_url") or find_existing_cached_product_image(brand, model)
    local_manual = package_asset_or_blank(v2_product, "manual_url") or find_existing_cached_manual(brand, model)
    legacy_package = load_overlay_package(brand, model)
    v2_overlay_path = product_package_root("toilet", brand, model) / "overlays.json"
    v2_overlay = None
    if v2_overlay_path.exists():
        try:
            v2_overlay = json.loads(v2_overlay_path.read_text(encoding="utf-8"))
        except Exception:
            v2_overlay = None

    overlay_package = v2_overlay or legacy_package
    source = "product_package" if v2_product else "starter_catalog"
    product_page_url = package_asset_or_blank(v2_product, "product_page_url") or (manual or {}).get("product_page_url", "")
    remote_photo_url = package_asset_or_blank(v2_product, "remote_photo_url") or (manual or {}).get("product_image_url", "")
    remote_manual_url = package_asset_or_blank(v2_product, "remote_manual_url") or (manual or {}).get("manual_url", "")

    return {
        "brand": brand,
        "model": model,
        "category": "toilet",
        "source": source,
        "photo": {
            "status": "cached" if local_image else "missing",
            "local_url": local_image,
            "remote_url": remote_photo_url,
            "product_page_url": product_page_url,
        },
        "manual": {
            "status": "cached" if local_manual else ("remote_available" if remote_manual_url else "missing"),
            "local_url": local_manual,
            "remote_url": remote_manual_url,
            "title": (manual or {}).get("manual_title", ""),
        },
        "overlay": {
            "status": "built" if overlay_package else "not_built",
            "tip_count": len((overlay_package or {}).get("installation_tips", [])),
            "hotspot_count": len((overlay_package or {}).get("overlays", [])),
            "package_url": public_catalog_file_url(v2_overlay_path) if v2_overlay else (public_catalog_package_url(overlay_package_path(brand, model)) if legacy_package else ""),
        },
        "confidence": (v2_product or {}).get("confidence") or ("HIGH" if local_image and local_manual and overlay_package else ("MEDIUM" if local_manual and overlay_package else "LOW")),
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


def local_static_path_for_url(url: str) -> Path | None:
    parsed_path = urlparse(url or "").path
    static_roots = [
        ("/static/images/", IMAGES_DIR),
        ("/static/catalog-images/", CATALOG_IMAGES_DIR),
        ("/static/catalog-manuals/", CATALOG_MANUALS_DIR),
        ("/static/catalog-packages/", CATALOG_PACKAGES_DIR),
        ("/static/catalog/", BASE_CATALOG_DIR),
        ("/static/canonical-images/", CANONICAL_IMAGE_DIR),
    ]
    for prefix, root in static_roots:
        if parsed_path.startswith(prefix):
            relative = parsed_path[len(prefix):].lstrip("/")
            return root / relative
    return None


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
    """Rank likely product photos ahead of category banners and site chrome.

    This intentionally favors exact model/SKU/product signals and penalizes
    broad category/lifestyle assets. The downloader will try several ranked
    candidates, so this score does not need to be perfect; it just needs to
    put plausible hero/product images near the top.
    """
    score = 0
    lower = url.lower()
    path = urlparse(url).path.lower()
    host = urlparse(url).netloc.lower()
    page_host = urlparse(product_page_url).netloc.lower()

    if page_host and (host == page_host or host.endswith('.' + page_host)):
        score += 30

    brand_tokens = [t for t in re.split(r"[^a-z0-9]+", (brand or "").lower()) if len(t) > 2]
    model_tokens = [t for t in re.split(r"[^a-z0-9]+", (model or "").lower()) if len(t) > 1]

    for token in brand_tokens:
        if token in lower:
            score += 8
    for token in model_tokens:
        if token in lower:
            score += 18

    # Product-photo cues.
    for term, points in [
        ("product", 14),
        ("toilet", 10),
        ("hero", 14),
        ("primary", 10),
        ("main", 8),
        ("white", 4),
        ("front", 5),
        ("sku", 6),
        ("shop/files", 4),
        ("products", 3),
    ]:
        if term in lower:
            score += points

    # Useful size hints from common CDN query params.
    for pattern in [r"width=(\d+)", r"w=(\d+)"]:
        match = re.search(pattern, lower)
        if match:
            try:
                width = int(match.group(1))
                if width >= 500:
                    score += 8
                elif width >= 250:
                    score += 3
            except Exception:
                pass

    if any(ext in path for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        score += 5

    # Penalize likely non-product assets.
    bad_terms = {
        'logo': 80,
        'icon': 70,
        'favicon': 90,
        'sprite': 80,
        'placeholder': 70,
        'spinner': 60,
        'banner': 35,
        'category': 30,
        'categories': 30,
        'lifestyle': 28,
        'room-scene': 28,
        'commercial-toilets': 35,
        'commercial_toilets': 35,
        'bathroom-toilets': 20,
        'environment': 22,
        'environmentcloseup': 45,
        'closeup': 40,
        'close-up': 40,
        'detail': 32,
        'parts': 25,
        'diagram': 28,
        'installation': 20,
        'social': 30,
        'facebook': 40,
        'instagram': 40,
        'youtube': 40,
        'twitter': 40,
        'payment': 40,
        'visa': 40,
        'mastercard': 40,
        'klarna': 40,
        'affirm': 40,
    }
    for term, penalty in bad_terms.items():
        if term in lower:
            score -= penalty

    # Very tiny thumbnails often contain size hints in filenames or params.
    if any(term in lower for term in ['thumb', 'thumbnail', 'small', 'swatch']):
        score -= 12

    if model_tokens and not any(token in lower for token in model_tokens):
        if any(term in lower for term in ['category', 'commercial', 'bathroom', 'environment', 'collection']):
            score -= 25

    return score


def cache_best_discovered_image(category: str, brand: str, model: str, image_candidates: list[str], max_attempts: int = 15, rejected: set[str] | None = None) -> dict:
    """Try ranked image candidates until one successfully downloads.

    This removes the manual extra step where Admin first discovers candidates
    and then asks a human to paste one. The manual override remains as a
    fallback, but normal product-page builds should cache a usable image
    automatically whenever one of the candidates is accessible. Rejected
    candidates are skipped so bad images do not keep getting reselected.
    """
    attempts = []
    unique = []
    seen = set()
    rejected = rejected or set()
    for url in image_candidates or []:
        if not url or url in seen or url in rejected:
            continue
        seen.add(url)
        unique.append(url)

    for index, candidate in enumerate(unique[:max_attempts], start=1):
        result = cache_product_image_to_package(category, brand, model, candidate)
        attempts.append({
            "rank": index,
            "url": candidate,
            "status": result.get("status", "unknown"),
            "local_url": result.get("local_url", ""),
            "error": result.get("error", ""),
        })
        if result.get("local_url"):
            result["attempted_count"] = index
            result["attempts"] = attempts
            result["selected_candidate"] = candidate
            return result

    return {
        "status": "unavailable",
        "local_url": "",
        "remote_url": unique[0] if unique else "",
        "error": "No discovered image candidate could be downloaded.",
        "attempted_count": len(attempts),
        "attempts": attempts,
        "selected_candidate": "",
    }


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
        local_url = public_catalog_file_url(out_path)
        quality = assess_and_record_image_quality(
            image_url=local_url,
            local_path=out_path,
            context={
                "source": "product_package_photo",
                "category": category,
                "brand": brand,
                "model": model,
                "remote_url": image_url,
                "editor_accepted": False,
            },
        )
        return {"status": "cached", "local_url": local_url, "remote_url": image_url, "error": "", "quality": quality}
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
        existing_discovery = load_discovery_json(category, brand, model)
        rejected = set(existing_discovery.get("rejected_image_candidates", []) or [])
        usable_images = [url for url in images if url not in rejected]
        discovery["images"] = usable_images
        discovery["rejected_image_candidates"] = list(rejected)
        discovery["rejected_count"] = len(rejected)
        discovery["pdfs"] = pdfs

        photo = cache_best_discovered_image(category, brand, model, usable_images, max_attempts=15, rejected=rejected)
        manual = cache_manual_to_package(category, brand, model, pdfs[0]["url"] if pdfs else "")
        discovery["photo"] = photo
        discovery["manual"] = manual
        discovery["photo_attempts"] = photo.get("attempts", [])
        discovery["photo_attempted_count"] = photo.get("attempted_count", 0)
        discovery["selected_photo_candidate"] = photo.get("selected_candidate", "") or photo.get("remote_url", "")
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
    overlays_document = {
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product_page_url,
        "installation_tips": overlay_payload.get("installation_tips", []),
        "overlays": overlay_payload.get("overlays", []),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (root / "overlays.json").write_text(json.dumps(overlays_document, indent=2), encoding="utf-8")
    package_manifest = save_product_package_manifest(
        category=category,
        brand=brand,
        model=model,
        product=product,
        discovery=discovery,
        overlays=overlays_document.get("overlays", []),
    )

    return {
        "status": discovery.get("status", "unknown"),
        "product": product,
        "discovery": discovery,
        "package_manifest": package_manifest,
        "product_json_url": public_catalog_file_url(root / "product.json"),
        "discovery_json_url": public_catalog_file_url(root / "discovery.json"),
        "overlays_json_url": public_catalog_file_url(root / "overlays.json"),
        "package_manifest_url": public_catalog_file_url(root / "package-manifest.json"),
    }


@app.post("/admin/catalog/build-product-page-package")
def post_catalog_build_product_page_package(request: ProductPagePackageRequest):
    return build_product_page_package(
        category=request.category,
        brand=request.brand,
        model=request.model,
        product_page_url=request.product_page_url,
    )




@app.post("/admin/catalog/test-build-niagara-stealth")
def post_catalog_test_build_niagara_stealth():
    """Verbose one-click test for the Niagara Original Stealth package.

    This endpoint deliberately avoids ambiguity from the frontend. It creates
    the expected folder, fetches the manufacturer product page, reports how
    many candidate images/PDFs were found, runs the package builder, and then
    reports exactly which files exist on the Render disk.
    """
    brand = "Niagara"
    model = "Original Stealth"
    category = "toilet"
    product_page_url = "https://niagaracorp.com/products/original-stealth-handle-round/"
    root = product_package_root(category, brand, model)

    report = {
        "status": "started",
        "brand": brand,
        "model": model,
        "category": category,
        "product_page_url": product_page_url,
        "root": str(root),
        "created_folder": False,
        "page_fetch_status": "not_started",
        "page_bytes": 0,
        "image_candidates": [],
        "pdf_candidates": [],
        "build_result": None,
        "files": {},
        "errors": [],
    }

    try:
        root.mkdir(parents=True, exist_ok=True)
        report["created_folder"] = root.exists()
    except Exception as exc:
        report["errors"].append(f"Could not create folder: {exc}")
        report["status"] = "failed"
        return report

    try:
        html = fetch_text_url(product_page_url)
        report["page_fetch_status"] = "ok"
        report["page_bytes"] = len(html.encode("utf-8", errors="ignore"))
        report["image_candidates"] = discover_image_candidates(html, product_page_url)
        report["pdf_candidates"] = discover_pdf_candidates(html, product_page_url)
    except Exception as exc:
        report["page_fetch_status"] = "failed"
        report["errors"].append(f"Could not fetch or parse product page: {exc}")

    try:
        report["build_result"] = build_product_page_package(
            category=category,
            brand=brand,
            model=model,
            product_page_url=product_page_url,
        )
    except Exception as exc:
        report["errors"].append(f"Package builder crashed: {exc}")

    expected_files = {
        "product_json": root / "product.json",
        "discovery_json": root / "discovery.json",
        "overlays_json": root / "overlays.json",
    }

    for label, path in expected_files.items():
        report["files"][label] = {
            "path": str(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "url": public_catalog_file_url(path) if path.exists() else "",
        }

    image_files = list((root / "images").glob("*")) if (root / "images").exists() else []
    manual_files = list((root / "manuals").glob("*")) if (root / "manuals").exists() else []
    report["files"]["images"] = [
        {"path": str(path), "bytes": path.stat().st_size, "url": public_catalog_file_url(path)}
        for path in image_files
    ]
    report["files"]["manuals"] = [
        {"path": str(path), "bytes": path.stat().st_size, "url": public_catalog_file_url(path)}
        for path in manual_files
    ]

    if report["errors"]:
        report["status"] = "completed_with_errors"
    elif report["files"]["product_json"]["exists"]:
        report["status"] = "complete"
    else:
        report["status"] = "no_package_written"

    return report



def get_product_page_for_package(category: str, brand: str, model: str) -> str:
    v2_product = load_product_page_product(category or "toilet", brand, model)
    if v2_product and v2_product.get("product_page_url"):
        return v2_product.get("product_page_url", "")
    if catalog_v2_category_slug(category) == "toilets":
        manual = find_toilet_manual(brand, model)
        return (manual or {}).get("product_page_url", "")
    return ""



def discovery_path_for_package(category: str, brand: str, model: str) -> Path:
    return product_package_root(category or "toilet", brand, model) / "discovery.json"


def product_json_path_for_package(category: str, brand: str, model: str) -> Path:
    return product_package_root(category or "toilet", brand, model) / "product.json"


def load_discovery_json(category: str, brand: str, model: str) -> dict:
    path = discovery_path_for_package(category, brand, model)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_discovery_json(category: str, brand: str, model: str, discovery: dict) -> dict:
    path = discovery_path_for_package(category, brand, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    discovery["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(discovery, indent=2), encoding="utf-8")
    return discovery


def rejected_photo_candidates(category: str, brand: str, model: str) -> set[str]:
    discovery = load_discovery_json(category, brand, model)
    return set(discovery.get("rejected_image_candidates", []) or [])


def recompute_product_confidence(product: dict) -> str:
    if product.get("photo_url") and product.get("manual_url"):
        return "HIGH"
    if product.get("photo_url") or product.get("manual_url"):
        return "MEDIUM"
    return "LOW"

def update_product_json_photo(category: str, brand: str, model: str, photo_result: dict) -> dict:
    root = product_package_root(category or "toilet", brand, model)
    root.mkdir(parents=True, exist_ok=True)
    product_path = root / "product.json"
    try:
        product = json.loads(product_path.read_text(encoding="utf-8")) if product_path.exists() else {}
    except Exception:
        product = {}
    product.update({
        "category": category or product.get("category", "toilet"),
        "brand": brand,
        "model": model,
        "photo_url": photo_result.get("local_url", "") or product.get("photo_url", ""),
        "remote_photo_url": photo_result.get("remote_url", "") or product.get("remote_photo_url", ""),
        "product_page_url": product.get("product_page_url", get_product_page_for_package(category, brand, model)),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    product["confidence"] = "HIGH" if product.get("photo_url") and product.get("manual_url") else ("MEDIUM" if product.get("photo_url") or product.get("manual_url") else "LOW")
    product_path.write_text(json.dumps(product, indent=2), encoding="utf-8")
    return product


@app.post("/admin/catalog/photo-diagnostics")
def post_catalog_photo_diagnostics(request: CatalogPhotoRequest):
    category = request.category or "toilet"
    brand = request.brand
    model = request.model
    root = product_package_root(category, brand, model)
    discovery_path = root / "discovery.json"
    product_path = root / "product.json"
    product = load_product_page_product(category, brand, model) or {}
    product_page_url = product.get("product_page_url") or get_product_page_for_package(category, brand, model)

    report = {
        "status": "started",
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product_page_url,
        "product_json_exists": product_path.exists(),
        "discovery_json_exists": discovery_path.exists(),
        "cached_photo_url": product.get("photo_url", ""),
        "remote_photo_url": product.get("remote_photo_url", ""),
        "image_candidates": [],
        "best_candidate": "",
        "download_status": "not_attempted",
        "failure_reason": "",
        "rejected_image_candidates": [],
        "rejected_count": 0,
    }

    if discovery_path.exists():
        try:
            discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
            rejected = set(discovery.get("rejected_image_candidates", []) or [])
            report["rejected_image_candidates"] = list(rejected)
            report["rejected_count"] = len(rejected)
            report["image_candidates"] = [url for url in (discovery.get("images", []) or []) if url not in rejected]
            report["best_candidate"] = (report["image_candidates"] or [""])[0]
            photo = discovery.get("photo", {}) or {}
            report["download_status"] = photo.get("status", "not_attempted")
            report["failure_reason"] = photo.get("error", "")
            report["attempted_count"] = photo.get("attempted_count", discovery.get("photo_attempted_count", 0))
            report["selected_candidate"] = photo.get("selected_candidate", discovery.get("selected_photo_candidate", ""))
            report["attempts"] = photo.get("attempts", discovery.get("photo_attempts", []))

            # If a previous diagnostics/build pass found candidates but never cached
            # a photo, do the intelligent retry here instead of making the editor
            # paste a URL manually. This keeps Diagnose Photo useful as both a
            # diagnostic and an auto-recovery action.
            if report["image_candidates"] and not report.get("cached_photo_url") and report["download_status"] != "cached":
                sorted_images = sorted(
                    report["image_candidates"],
                    key=lambda u: score_image_candidate(u, brand, model, product_page_url),
                    reverse=True,
                )
                photo = cache_best_discovered_image(category, brand, model, sorted_images, max_attempts=15, rejected=rejected)
                product = update_product_json_photo(category, brand, model, photo)
                discovery["images"] = sorted_images
                discovery["photo"] = photo
                discovery["photo_attempted_count"] = photo.get("attempted_count", 0)
                discovery["selected_photo_candidate"] = photo.get("selected_candidate", "") or photo.get("remote_url", "")
                discovery["photo_attempts"] = photo.get("attempts", [])
                discovery["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                discovery_path.write_text(json.dumps(discovery, indent=2), encoding="utf-8")
                report["image_candidates"] = sorted_images
                report["best_candidate"] = (sorted_images or [""])[0]
                report["download_status"] = photo.get("status", "unknown")
                report["failure_reason"] = photo.get("error", "")
                report["cached_photo_url"] = photo.get("local_url", "") or product.get("photo_url", "")
                report["remote_photo_url"] = photo.get("remote_url", "") or product.get("remote_photo_url", "")
                report["attempted_count"] = photo.get("attempted_count", 0)
                report["selected_candidate"] = photo.get("selected_candidate", "")
                report["attempts"] = photo.get("attempts", [])
        except Exception as exc:
            report["failure_reason"] = f"Could not read discovery.json: {exc}"

    if not report["image_candidates"] and product_page_url:
        try:
            rejected = rejected_photo_candidates(category, brand, model)
            report["rejected_image_candidates"] = list(rejected)
            report["rejected_count"] = len(rejected)
            html = fetch_text_url(product_page_url)
            images = discover_image_candidates(html, product_page_url)
            images = sorted(images, key=lambda u: score_image_candidate(u, brand, model, product_page_url), reverse=True)
            images = [url for url in images if url not in rejected]
            report["image_candidates"] = images
            report["best_candidate"] = (images or [""])[0]
            if images:
                photo = cache_best_discovered_image(category, brand, model, images, max_attempts=15)
                product = update_product_json_photo(category, brand, model, photo)
                report["download_status"] = photo.get("status", "unknown")
                report["failure_reason"] = photo.get("error", "")
                report["cached_photo_url"] = photo.get("local_url", "") or product.get("photo_url", "")
                report["remote_photo_url"] = photo.get("remote_url", "") or product.get("remote_photo_url", "")
                report["attempted_count"] = photo.get("attempted_count", 0)
                report["selected_candidate"] = photo.get("selected_candidate", "")
                report["attempts"] = photo.get("attempts", [])
            else:
                report["download_status"] = "no_candidates"
                report["failure_reason"] = "No usable manufacturer image candidates were discovered on the product page. Try pasting a manufacturer-hosted image URL."
        except Exception as exc:
            report["download_status"] = "failed"
            report["failure_reason"] = f"Could not fetch or parse product page: {exc}"

    report["status"] = "loaded"
    return report


@app.post("/admin/catalog/cache-photo-url")
def post_catalog_cache_photo_url(request: CatalogPhotoRequest):
    if not request.image_url.strip():
        return {"status": "missing_image_url", "error": "Paste a manufacturer-hosted image URL first."}
    result = cache_product_image_to_package(request.category or "toilet", request.brand, request.model, request.image_url.strip())
    product = update_product_json_photo(request.category or "toilet", request.brand, request.model, result)

    root = product_package_root(request.category or "toilet", request.brand, request.model)
    discovery_path = root / "discovery.json"
    try:
        discovery = json.loads(discovery_path.read_text(encoding="utf-8")) if discovery_path.exists() else {}
    except Exception:
        discovery = {}
    discovery.setdefault("images", [])
    rejected = set(discovery.get("rejected_image_candidates", []) or [])
    rejected.discard(request.image_url.strip())
    discovery["rejected_image_candidates"] = list(rejected)
    discovery["rejected_count"] = len(rejected)
    if request.image_url.strip() not in discovery["images"]:
        discovery["images"].insert(0, request.image_url.strip())
    discovery["manual_photo_override"] = request.image_url.strip()
    discovery["photo"] = result
    discovery["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    discovery_path.write_text(json.dumps(discovery, indent=2), encoding="utf-8")

    log_correction_memory({
        "action": "product_photo_cached",
        "category": request.category or "toilet",
        "brand": request.brand,
        "model": request.model,
        "manual_photo_override": request.image_url.strip(),
        "cached_photo_url": result.get("local_url", ""),
        "remote_photo_url": result.get("remote_url", ""),
        "status": result.get("status"),
        "error": result.get("error", ""),
    })
    log_editor_decision({
        "action": "product_photo_cached",
        "category": request.category or "toilet",
        "brand": request.brand,
        "model": request.model,
        "cached_photo_url": result.get("local_url", ""),
    })
    product_photo_example(
        "accepted",
        request.category or "toilet",
        request.brand,
        request.model,
        {
            "remote_photo_url": result.get("remote_url", ""),
            "cached_photo_url": result.get("local_url", ""),
            "quality": result.get("quality", {}),
            "source": "manual_override" if discovery.get("manual_photo_override") else "candidate_cache",
        },
    )

    return {
        "status": result.get("status"),
        "photo": result,
        "product": product,
        "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model) if catalog_v2_category_slug(request.category) == "toilets" else {},
    }


@app.post("/admin/catalog/reject-photo-candidates")
def post_catalog_reject_photo_candidates(request: CatalogPhotoRequest):
    """Reject all currently discovered photo candidates for a product.

    This is an editorial override: the current discovered set is marked as
    unusable, product.json is cleared of the cached photo, and future automatic
    selection skips those URLs. A manual image URL can still be pasted and
    cached afterward.
    """
    category = request.category or "toilet"
    brand = request.brand
    model = request.model
    root = product_package_root(category, brand, model)
    root.mkdir(parents=True, exist_ok=True)
    discovery = load_discovery_json(category, brand, model)
    product = load_product_page_product(category, brand, model) or {}

    current_images = set(discovery.get("images", []) or [])
    current_remote = product.get("remote_photo_url") or discovery.get("selected_photo_candidate") or (discovery.get("photo", {}) or {}).get("remote_url", "")
    if current_remote:
        current_images.add(current_remote)

    rejected = set(discovery.get("rejected_image_candidates", []) or [])
    rejected.update(url for url in current_images if url)

    discovery["rejected_image_candidates"] = list(rejected)
    discovery["rejected_count"] = len(rejected)
    discovery["photo"] = {
        "status": "rejected",
        "local_url": "",
        "remote_url": current_remote or "",
        "error": "All discovered image candidates were rejected by an editor.",
    }
    discovery["selected_photo_candidate"] = ""
    discovery["photo_attempts"] = []
    save_discovery_json(category, brand, model, discovery)

    product_path = product_json_path_for_package(category, brand, model)
    product.update({
        "category": category,
        "brand": brand,
        "model": model,
        "product_page_url": product.get("product_page_url") or get_product_page_for_package(category, brand, model),
        "photo_url": "",
        "remote_photo_url": "",
        "photo_rejected": True,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    product["confidence"] = recompute_product_confidence(product)
    product_path.parent.mkdir(parents=True, exist_ok=True)
    product_path.write_text(json.dumps(product, indent=2), encoding="utf-8")

    log_correction_memory({
        "action": "product_photo_candidates_rejected",
        "category": category,
        "brand": brand,
        "model": model,
        "rejected_count": len(rejected),
        "rejected_image_candidates": list(rejected),
    })
    log_editor_decision({
        "action": "product_photo_candidates_rejected",
        "category": category,
        "brand": brand,
        "model": model,
        "rejected_count": len(rejected),
    })
    product_photo_example(
        "rejected_candidates",
        category,
        brand,
        model,
        {
            "rejected_count": len(rejected),
            "rejected_image_candidates": list(rejected),
            "current_remote_photo_url": current_remote or "",
        },
    )

    return {
        "status": "rejected",
        "brand": brand,
        "model": model,
        "category": category,
        "rejected_count": len(rejected),
        "product": product,
        "pipeline_status": get_toilet_catalog_pipeline_status(brand, model) if catalog_v2_category_slug(category) == "toilets" else {},
    }

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

    product_page_url = get_product_page_for_package(request.category or "toilet", request.brand, request.model) or manual.get("product_page_url", "")

    # Prefer the v2 product-page package builder whenever a manufacturer
    # product page exists. It discovers many image candidates, tries them in
    # ranked order, caches the first usable photo, caches manuals, and writes
    # product/discovery/overlay JSON.
    if product_page_url:
        package_result = build_product_page_package(
            category=request.category or "toilet",
            brand=request.brand,
            model=request.model,
            product_page_url=product_page_url,
        )
        return {
            "status": package_result.get("status", "complete"),
            "brand": request.brand,
            "model": request.model,
            "product_package": package_result,
            "photo": package_result.get("discovery", {}).get("photo", {}),
            "manual": package_result.get("discovery", {}).get("manual", {}),
            "pipeline_status": get_toilet_catalog_pipeline_status(request.brand, request.model),
        }

    # Fallback for older records with no product page.
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
    taxonomy_match = classify_taxonomy_query(query)

    if is_toilet_query(query):
        options = toilet_product_options(query)
        return {
            **options,
            "taxonomy_match": taxonomy_match,
            "requires_branch_selection": taxonomy_match.get("status") == "branch_selection_required",
            "branch_question": taxonomy_match.get("question", ""),
            "branches": taxonomy_match.get("branches", []),
        }

    options = get_product_options_for_query(query)

    return {
        "query": query,
        "category": options.get("category", "generic"),
        "brands": options.get("brands", []),
        "query_has_known_brand_and_model":
            query_has_known_brand_and_model(query),
        "taxonomy_match": taxonomy_match,
        "requires_branch_selection": taxonomy_match.get("status") == "branch_selection_required",
        "branch_question": taxonomy_match.get("question", ""),
        "branches": taxonomy_match.get("branches", []),
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


@app.get("/admin/correction-memory")
def get_admin_correction_memory(limit: int = 100):
    """Return recent correction-memory records for admin review."""
    records = []
    if CORRECTION_MEMORY_FILE.exists():
        try:
            lines = CORRECTION_MEMORY_FILE.read_text(encoding="utf-8").splitlines()
            for line in lines[-limit:]:
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    records.append({"raw": line})
        except Exception as exc:
            return {"status": "error", "error": str(exc), "records": []}
    return {"status": "loaded", "records": records}


@app.get("/admin/category-rules")
def get_admin_category_rules():
    return {"status": "loaded", "rules": load_category_rules()}


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


@app.post("/admin/source-research")
def post_source_research(request: SourceResearchRequest, _: None = Depends(require_admin_token)):
    return discover_source_research(
        request.query,
        force_refresh=request.force_refresh,
    )


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


@app.post("/admin/rebuild-walkthrough-index")
def post_rebuild_walkthrough_index(_: None = Depends(require_admin_token)):
    return rebuild_walkthrough_index_from_storage()


@app.get("/admin/walkthrough-library")
def get_walkthrough_library(limit: int = 1000, _: None = Depends(require_admin_token)):
    return walkthrough_library(limit=limit)


@app.get("/admin/taxonomy-integrity")
def get_taxonomy_integrity(_: None = Depends(require_admin_token)):
    return taxonomy_integrity_report()


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


@app.post("/admin/save-walkthrough")
def post_save_admin_walkthrough(request: SaveWalkthroughRequest, _: None = Depends(require_admin_token)):
    manifest = dict(request.walkthrough or {})
    requested_id = (
        manifest.get("storage_walkthrough_id")
        or manifest.get("walkthrough_id")
        or manifest.get("title")
        or manifest.get("query")
        or ""
    )
    walkthrough_id = resolve_walkthrough_storage_id(requested_id)
    before_manifest = load_walkthrough_by_id(walkthrough_id) or {}

    if not requested_id:
        return {"status": "error", "error": "Missing walkthrough id, title, or query."}

    manifest["walkthrough_id"] = manifest.get("walkthrough_id") or walkthrough_id
    manifest["quality_status"] = manifest.get("quality_status") or "editor_reviewed"
    if manifest.get("review_status", "draft") not in ["approved", "deleted", "deprecated"]:
        manifest["review_status"] = manifest.get("review_status") or "edited"

    manifest["steps"] = normalize_step_numbering(manifest.get("steps", []) or [])

    manifest["version"] = int(manifest.get("version", 1)) + 1
    manifest["editor_saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    save_walkthrough(walkthrough_id, manifest)
    log_editor_decision({
        "action": "repair_editor_saved",
        "walkthrough_id": walkthrough_id,
        "review_status": manifest.get("review_status", ""),
        "quality_status": manifest.get("quality_status", ""),
        "step_count": len(manifest.get("steps", []) or []),
    })
    walkthrough_edit_example(
        "repair_editor_saved",
        before_manifest,
        manifest,
        {
            "source": "walkthrough_repair_editor",
            "requested_walkthrough_id": requested_id,
        }
    )
    learning_result = learn_editor_rules(
        "repair_editor_saved",
        before_manifest,
        manifest,
        {
            "source": "walkthrough_repair_editor",
            "requested_walkthrough_id": requested_id,
        },
    )

    return {
        "status": "saved",
        "walkthrough_id": walkthrough_id,
        "walkthrough": manifest,
        "editor_learning": learning_result,
    }


@app.post("/admin/qc/save-all")
def post_qc_save_all(request: QcSaveAllRequest, _: None = Depends(require_admin_token)):
    results = []

    for item in request.actions:
        requested_walkthrough_id = item.walkthrough_id
        walkthrough_id = resolve_walkthrough_storage_id(requested_walkthrough_id)
        manifest = load_walkthrough_by_id(walkthrough_id)
        if not manifest:
            results.append({
                "walkthrough_id": walkthrough_id,
                "requested_walkthrough_id": requested_walkthrough_id,
                "status": "not_found",
            })
            continue

        before_manifest = json.loads(json.dumps(manifest))
        action = (item.action or "").lower().strip()
        current_status = manifest.get("review_status", "draft")

        if item.title is not None:
            manifest["title"] = item.title.strip()
        if item.query is not None:
            add_manifest_alias(manifest, manifest.get("query", ""))
            manifest["query"] = item.query.strip()
            add_manifest_alias(manifest, manifest["query"])
        if item.visual_template is not None:
            manifest["visual_template"] = item.visual_template.strip()

        if item.steps:
            previous_validation = manifest.get("step_sequence_validation") or {}
            previous_issues = previous_validation.get("issues", []) or []
            manifest["steps"] = normalize_step_numbering(item.steps)
            manifest["step_sequence_validation"] = {
                "status": "editor_reviewed",
                "category": (manifest.get("step_sequence_validation") or {}).get("category", "generic"),
                "issues": previous_issues,
                "automated_status": previous_validation.get("status", ""),
                "automated_issues": previous_issues,
                "editor_decision": action or "save",
                "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        if action == "approve":
            duplicate_id = find_approved_duplicate_for_manifest(
                manifest,
                exclude_walkthrough_id=walkthrough_id
            )
            if duplicate_id:
                canonical_manifest = load_walkthrough_by_id(duplicate_id) or {}
                for alias_value in [
                    requested_walkthrough_id,
                    walkthrough_id,
                    before_manifest.get("title", ""),
                    before_manifest.get("query", ""),
                    manifest.get("title", ""),
                    manifest.get("query", ""),
                    *(before_manifest.get("aliases", []) or []),
                    *(manifest.get("aliases", []) or []),
                ]:
                    add_manifest_alias(canonical_manifest, alias_value)

                canonical_manifest["version"] = int(canonical_manifest.get("version", 1)) + 1
                canonical_manifest["alias_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                save_walkthrough(duplicate_id, canonical_manifest)

                manifest["review_status"] = "deprecated"
                manifest["quality_status"] = "merged_with_approved_walkthrough"
                manifest["duplicate_of_walkthrough_id"] = duplicate_id
                manifest["deprecated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                manifest["version"] = int(manifest.get("version", 1)) + 1
                save_walkthrough(walkthrough_id, manifest)

                log_editor_decision({
                    "action": "qc_merged_duplicate",
                    "walkthrough_id": walkthrough_id,
                    "canonical_walkthrough_id": duplicate_id,
                    "review_status": manifest.get("review_status", ""),
                    "quality_status": manifest.get("quality_status", ""),
                    "step_count": len(manifest.get("steps", []) or []),
                })
                walkthrough_edit_example(
                    "qc_merged_duplicate",
                    before_manifest,
                    canonical_manifest,
                    {
                        "source": "step_order_quality_control",
                        "requested_walkthrough_id": requested_walkthrough_id,
                        "canonical_walkthrough_id": duplicate_id,
                    }
                )
                learning_result = learn_editor_rules(
                    "qc_merged_duplicate",
                    before_manifest,
                    canonical_manifest,
                    {
                        "source": "step_order_quality_control",
                        "requested_walkthrough_id": requested_walkthrough_id,
                        "canonical_walkthrough_id": duplicate_id,
                    },
                )
                results.append({
                    "walkthrough_id": duplicate_id,
                    "deprecated_walkthrough_id": walkthrough_id,
                    "requested_walkthrough_id": requested_walkthrough_id,
                    "status": "merged_duplicate",
                    "review_status": canonical_manifest.get("review_status"),
                    "quality_status": canonical_manifest.get("quality_status"),
                    "editor_learning": learning_result,
                    "message": "Matched an existing approved walkthrough; added this phrasing as an alias and deprecated the duplicate draft.",
                })
                continue

            manifest["review_status"] = "approved"
            manifest["quality_status"] = "approved_for_next_stage"
            manifest["next_stage"] = "product_specific_overlay"
            manifest["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            result_status = "approved"
        elif action == "delete":
            if current_status == "approved":
                results.append({
                    "walkthrough_id": walkthrough_id,
                    "requested_walkthrough_id": requested_walkthrough_id,
                    "status": "skipped",
                    "message": "Approved walkthroughs cannot be deleted from QC."
                })
                continue
            deletion = delete_walkthrough(walkthrough_id)
            log_editor_decision({
                "action": "qc_deleted",
                "walkthrough_id": walkthrough_id,
                "review_status": current_status,
                "quality_status": manifest.get("quality_status", ""),
                "step_count": len(manifest.get("steps", []) or []),
                "deleted": deletion.get("deleted", False),
            })
            walkthrough_edit_example(
                "qc_deleted",
                before_manifest,
                {},
                {
                    "source": "step_order_quality_control",
                    "requested_walkthrough_id": requested_walkthrough_id,
                    "deleted": deletion.get("deleted", False),
                }
            )
            results.append({
                "walkthrough_id": walkthrough_id,
                "requested_walkthrough_id": requested_walkthrough_id,
                "status": "deleted",
                "deleted": deletion.get("deleted", False),
            })
            continue
        elif action == "save":
            if current_status not in ["approved", "deleted"]:
                manifest["review_status"] = "edited"
            manifest["quality_status"] = "editor_reviewed"
            result_status = "saved"
        else:
            results.append({
                "walkthrough_id": walkthrough_id,
                "requested_walkthrough_id": requested_walkthrough_id,
                "status": "skipped",
                "message": f"Unknown QC action: {item.action}"
            })
            continue

        manifest["version"] = int(manifest.get("version", 1)) + 1
        manifest["qc_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_walkthrough(walkthrough_id, manifest)
        alias_candidate = None
        if item.query is not None:
            alias_candidate = record_query_alias_candidate(
                walkthrough_id,
                before_manifest,
                manifest,
                "step_order_quality_control",
            )
        log_editor_decision({
            "action": f"qc_{result_status}",
            "walkthrough_id": walkthrough_id,
            "review_status": manifest.get("review_status", ""),
            "quality_status": manifest.get("quality_status", ""),
            "step_count": len(manifest.get("steps", []) or []),
            "query_alias_candidate_id": (alias_candidate or {}).get("id", ""),
        })
        walkthrough_edit_example(
            f"qc_{result_status}",
            before_manifest,
            manifest,
            {
                "source": "step_order_quality_control",
                "requested_walkthrough_id": requested_walkthrough_id,
                "submitted_step_count": len(item.steps or []),
                "query_alias_candidate_id": (alias_candidate or {}).get("id", ""),
            }
        )
        learning_result = learn_editor_rules(
            f"qc_{result_status}",
            before_manifest,
            manifest,
            {
                "source": "step_order_quality_control",
                "requested_walkthrough_id": requested_walkthrough_id,
                "submitted_step_count": len(item.steps or []),
                "query_alias_candidate_id": (alias_candidate or {}).get("id", ""),
            },
        )
        results.append({
            "walkthrough_id": walkthrough_id,
            "requested_walkthrough_id": requested_walkthrough_id,
            "status": result_status,
            "review_status": manifest.get("review_status"),
            "quality_status": manifest.get("quality_status"),
            "editor_learning": learning_result,
        })

    return {
        "status": "saved",
        "processed_count": len([item for item in results if item.get("status") in ["approved", "deleted", "saved", "merged_duplicate"]]),
        "results": results,
    }


@app.post("/admin/qc/mark-all-drafts")
def post_qc_mark_all_drafts(_: None = Depends(require_admin_token)):
    items = list_walkthrough_manifests(limit=10000)
    updated = []
    skipped = []

    for item in items:
        walkthrough_id = item.get("walkthrough_id", "")
        manifest = load_walkthrough_by_id(walkthrough_id)
        if not manifest:
            skipped.append({"walkthrough_id": walkthrough_id, "status": "not_found"})
            continue

        current_status = (manifest.get("review_status") or "draft").lower()
        if current_status in ["approved", "deleted", "deprecated"]:
            skipped.append({"walkthrough_id": walkthrough_id, "status": current_status})
            continue

        manifest["review_status"] = "draft"
        manifest["quality_status"] = "awaiting_qc"
        manifest["qc_stage"] = "step_order_review"
        manifest["draft_marked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_walkthrough(walkthrough_id, manifest)
        updated.append(walkthrough_id)

    log_editor_decision({
        "action": "qc_mark_all_drafts",
        "updated_count": len(updated),
        "skipped_count": len(skipped),
    })

    return {
        "status": "drafts_marked",
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "updated": updated,
        "skipped": skipped,
    }


@app.get("/admin/qc/visual-migration-report")
def get_qc_visual_migration_report(
    limit: int = 10000,
    review_status: str = "all",
    _: None = Depends(require_admin_token),
):
    return visual_migration_report(limit=limit, review_status=review_status)


@app.post("/admin/qc/prepare-visual-migration")
def post_qc_prepare_visual_migration(
    request: QcVisualMigrationRequest,
    _: None = Depends(require_admin_token),
):
    return prepare_visual_migration_batch(request)


@app.post("/admin/qc/adopt-approved-match")
def post_qc_adopt_approved_match(request: AdoptApprovedMatchRequest, _: None = Depends(require_admin_token)):
    requested_id = request.walkthrough_id
    walkthrough_id = resolve_walkthrough_storage_id(requested_id)
    stored_manifest = load_walkthrough_by_id(walkthrough_id) or {}
    candidate_manifest = dict(request.walkthrough or stored_manifest or {})

    if not candidate_manifest:
        return {
            "status": "not_found",
            "walkthrough_id": walkthrough_id,
        }

    candidate_manifest["walkthrough_id"] = candidate_manifest.get("walkthrough_id") or walkthrough_id
    duplicate_id = find_approved_duplicate_for_manifest(
        candidate_manifest,
        exclude_walkthrough_id=walkthrough_id,
    )

    if not duplicate_id:
        return {
            "status": "no_match",
            "walkthrough_id": walkthrough_id,
            "message": "No approved equivalent walkthrough was found.",
        }

    approved_manifest = load_walkthrough_by_id(duplicate_id) or {}
    if not approved_manifest:
        return {
            "status": "not_found",
            "walkthrough_id": walkthrough_id,
            "approved_walkthrough_id": duplicate_id,
        }

    adopted = json.loads(json.dumps(candidate_manifest))
    adopted["steps"] = normalize_step_numbering(json.loads(json.dumps(approved_manifest.get("steps", []) or [])))
    adopted["adopted_from_walkthrough_id"] = duplicate_id
    adopted["adopted_from_title"] = approved_manifest.get("title", duplicate_id)
    adopted["quality_status"] = "matched_approved_walkthrough"
    adopted["source_approved_at"] = approved_manifest.get("approved_at", "")
    add_manifest_alias(adopted, approved_manifest.get("query", ""))
    add_manifest_alias(adopted, approved_manifest.get("title", ""))

    return {
        "status": "matched",
        "walkthrough_id": walkthrough_id,
        "approved_walkthrough_id": duplicate_id,
        "approved_title": approved_manifest.get("title", duplicate_id),
        "approved_query": approved_manifest.get("query", ""),
        "step_count": len(adopted.get("steps", []) or []),
        "image_count": len([
            step for step in adopted.get("steps", []) or []
            if step.get("imageUrl")
        ]),
        "walkthrough": adopted,
    }


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
    inferred_category = infer_construction_category(
        walkthrough_id=request.walkthrough_id,
        title=manifest.get("title", ""),
        query=manifest.get("query", ""),
    )
    category_rule_prompt = format_rules_for_prompt(inferred_category)

    # Keep prompts short and explicitly safe. This reduces false moderation hits
    # and prevents long prompt-derived image filenames in image_generator.py.
    repair_prompt = " ".join((
        f"{original_prompt}. Correction request: {correction}. "
        f"{category_rule_prompt} "
        "Professional residential construction training illustration. "
        "Show realistic materials, accurate tool placement, safe work positioning, no injuries, no weapons, no illegal activity."
    ).split())
    repair_prompt = repair_prompt.replace("house wrap", "weather-resistive wall barrier")
    repair_prompt = repair_prompt.replace("House wrap", "weather-resistive wall barrier")
    repair_prompt = repair_prompt[:900].rstrip(" ,;:-")

    new_image_url = generate_step_image(repair_prompt, int(request.step_id))

    target["imagePrompt"] = original_prompt
    target["pendingImageUrl"] = new_image_url
    target["pendingImagePrompt"] = repair_prompt
    target["pendingCorrection"] = correction

    log_correction_memory({
        "action": "image_regeneration_requested",
        "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
        "category": inferred_category,
        "step_id": request.step_id,
        "step_instruction": target.get("instruction", ""),
        "step_detail": target.get("detail", ""),
        "image_label": target.get("imageLabel", ""),
        "original_prompt": original_prompt,
        "correction": correction,
        "category_rules_applied": category_rules_for(inferred_category),
        "pending_image_url": new_image_url,
    })

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


def build_qc_step_image_prompt(
    walkthrough_id: str,
    title: str,
    query: str,
    step_id: int,
    label: str,
    instruction: str,
    detail: str,
    image_direction: str = "",
    category_rule_prompt: str = "",
    visual_template: str = "",
    visual_assets: dict | None = None,
) -> str:
    visual_assets = visual_assets or {}
    visual_template = (visual_template or "").strip()
    continuity_prompt = (
        "Walkthrough visual continuity contract: "
        "All steps in this walkthrough must depict the same primary object, same fixture/product shape, same surrounding installation setting, and same recurring worker/character style unless the step explicitly replaces or removes that object. "
        "Do not switch product variants between steps, such as changing a countertop drop-in sink into a wall-hung sink. "
    )
    if visual_template:
        continuity_prompt += f"Locked walkthrough visual template: {visual_template}. "
    if visual_assets:
        asset_parts = [
            "Use the approved walkthrough asset sheet as the visual bible.",
            f"Primary object: {visual_assets.get('primary_object', '')}.",
            f"Product: {visual_assets.get('product', '')}.",
            f"Environment: {visual_assets.get('environment', '')}.",
            f"Worker: {visual_assets.get('worker', '')}.",
            "Do not redesign these assets between regenerated step images.",
        ]
        tools = visual_assets.get("tools", []) or []
        if tools:
            asset_parts.append("Tools/materials: " + "; ".join(map(str, tools)) + ".")
        continuity_prompt += " ".join(" ".join(asset_parts).split()) + " "

    image_prompt_parts = [
        f"{title or query or walkthrough_id}.",
        continuity_prompt,
        f"Step {step_id}: {label}.",
        f"Instruction: {instruction}. Detail: {detail}.",
    ]
    if image_direction:
        image_prompt_parts.append(f"Editor image direction: {image_direction}.")
    image_prompt_parts.extend([
        category_rule_prompt,
        "Professional residential construction training illustration.",
        "Use the established RocketSurgery walkthrough style: high-quality rendered illustration, clean neutral jobsite background, realistic residential materials, clear single-step composition, consistent perspective, crisp tool and material placement, no decorative clutter.",
        "Show accurate tool placement, safe work positioning, no injuries, no weapons, no illegal activity.",
    ])
    return " ".join(" ".join(image_prompt_parts).split())


@app.post("/admin/qc/generate-step-image")
def post_generate_qc_step_image(request: GenerateQcStepImageRequest, _: None = Depends(require_admin_token)):
    step = dict(request.step or {})
    step_id = int(step.get("id") or 1)
    inferred_category = infer_construction_category(
        walkthrough_id=request.walkthrough_id,
        title=request.title,
        query=request.query,
    )
    category_rule_prompt = format_rules_for_prompt(inferred_category)
    label = step.get("imageLabel") or step.get("instruction") or f"Step {step_id}"
    instruction = step.get("instruction", "")
    detail = step.get("detail", "")
    image_direction = (request.image_direction or step.get("imageDirection") or "").strip()
    image_prompt = build_qc_step_image_prompt(
        walkthrough_id=request.walkthrough_id,
        title=request.title,
        query=request.query,
        step_id=step_id,
        label=label,
        instruction=instruction,
        detail=detail,
        image_direction=image_direction,
        category_rule_prompt=category_rule_prompt,
        visual_template=request.visual_template,
        visual_assets=request.visual_assets,
    )
    image_prompt = image_prompt.replace("house wrap", "weather-resistive wall barrier")
    image_prompt = image_prompt.replace("House wrap", "weather-resistive wall barrier")
    image_prompt = image_prompt[:1400].rstrip(" ,;:-")

    visual_assets = request.visual_assets or {}
    visual_template = (request.visual_template or "").strip()
    image_url = generate_step_image_from_asset_sheet(
        image_prompt,
        step_id,
        asset_sheet_url=visual_assets.get("asset_sheet_url", ""),
        cache_key_suffix=f"qc-{request.walkthrough_id}-{step_id}-{int(time.time())}",
    )
    log_correction_memory({
        "action": "qc_step_image_generated",
        "walkthrough_id": request.walkthrough_id,
        "category": inferred_category,
        "step_id": step_id,
        "step_instruction": instruction,
        "step_detail": detail,
        "image_label": label,
        "image_direction": image_direction,
        "visual_template": visual_template,
        "visual_assets": visual_assets,
        "image_prompt": image_prompt,
        "image_url": image_url,
    })

    return {
        "status": "generated",
        "step_id": step_id,
        "image_url": image_url,
        "visual_template": visual_template,
        "visual_assets": visual_assets,
        "image_prompt": image_prompt,
    }


@app.post("/admin/qc/regenerate-all-images")
def post_regenerate_all_qc_images(request: RegenerateAllQcImagesRequest, _: None = Depends(require_admin_token)):
    inferred_category = infer_construction_category(
        walkthrough_id=request.walkthrough_id,
        title=request.title,
        query=request.query,
    )
    category_rule_prompt = format_rules_for_prompt(inferred_category)
    visual_assets = request.visual_assets or {}
    visual_template = (request.visual_template or "").strip()
    revision_key = f"qc-all-{request.walkthrough_id}-{int(time.time())}"
    updated_steps = []

    for index, original_step in enumerate(request.steps or [], start=1):
        step = dict(original_step or {})
        step_id = int(step.get("id") or index)
        label = step.get("imageLabel") or step.get("instruction") or f"Step {step_id}"
        instruction = step.get("instruction", "")
        detail = step.get("detail", "")
        image_direction = str(step.get("imageDirection") or "").strip()
        image_prompt = build_qc_step_image_prompt(
            walkthrough_id=request.walkthrough_id,
            title=request.title,
            query=request.query,
            step_id=step_id,
            label=label,
            instruction=instruction,
            detail=detail,
            image_direction=image_direction,
            category_rule_prompt=category_rule_prompt,
            visual_template=visual_template,
            visual_assets=visual_assets,
        )
        image_prompt = image_prompt.replace("house wrap", "weather-resistive wall barrier")
        image_prompt = image_prompt.replace("House wrap", "weather-resistive wall barrier")
        image_prompt = image_prompt[:1400].rstrip(" ,;:-")
        image_url = generate_step_image_from_asset_sheet(
            image_prompt,
            step_id,
            asset_sheet_url=visual_assets.get("asset_sheet_url", ""),
            cache_key_suffix=f"{revision_key}-{step_id}",
        )
        updated_steps.append({
            **step,
            "imageUrl": image_url,
            "imagePrompt": image_prompt,
            "imageStale": False,
        })

    log_correction_memory({
        "action": "qc_all_step_images_generated",
        "walkthrough_id": request.walkthrough_id,
        "category": inferred_category,
        "step_count": len(updated_steps),
        "visual_template": visual_template,
        "visual_assets": visual_assets,
        "revision_key": revision_key,
    })

    return {
        "status": "generated",
        "walkthrough_id": request.walkthrough_id,
        "step_count": len(updated_steps),
        "steps": updated_steps,
        "visual_template": visual_template,
        "visual_assets": visual_assets,
        "revision_key": revision_key,
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

            inferred_category = infer_construction_category(
                walkthrough_id=request.walkthrough_id,
                title=manifest.get("title", ""),
                query=manifest.get("query", ""),
            )
            log_correction_memory({
                "action": "image_accepted",
                "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                "category": inferred_category,
                "step_id": request.step_id,
                "accepted_image_url": pending,
                "previous_image_url": previous,
                "image_prompt": step.get("imagePrompt", ""),
                "step_instruction": step.get("instruction", ""),
                "step_detail": step.get("detail", ""),
                "image_label": step.get("imageLabel", ""),
            })
            log_editor_decision({
                "action": "image_accepted",
                "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                "category": inferred_category,
                "step_id": request.step_id,
                "accepted_image_url": pending,
            })
            quality = assess_and_record_image_quality(
                image_url=pending,
                local_path=local_static_path_for_url(pending) or "",
                context={
                    "source": "repair_editor_acceptance",
                    "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                    "category": inferred_category,
                    "step_id": request.step_id,
                    "query": manifest.get("query", ""),
                    "step_instruction": step.get("instruction", ""),
                    "step_detail": step.get("detail", ""),
                    "image_label": step.get("imageLabel", ""),
                    "image_prompt": step.get("imagePrompt", ""),
                    "editor_accepted": True,
                },
            )
            image_repair_example(
                "accepted",
                manifest,
                step,
                before_image_url=previous,
                after_image_url=pending,
                correction=step.get("imageRepairHistory", [{}])[-1].get("correctionPrompt", "") if step.get("imageRepairHistory") else "",
            )
            step["imageQuality"] = quality

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
                pending_url = step.get("pendingImageUrl", "")
                pending_prompt = step.get("pendingImagePrompt", "")
                pending_correction = step.get("pendingCorrection", "")
                step.pop("pendingImageUrl", None)
                step.pop("pendingImagePrompt", None)
                step.pop("pendingCorrection", None)
                inferred_category = infer_construction_category(
                    walkthrough_id=request.walkthrough_id,
                    title=manifest.get("title", ""),
                    query=manifest.get("query", ""),
                )
                log_correction_memory({
                    "action": "image_rejected_pending",
                    "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                    "category": inferred_category,
                    "step_id": request.step_id,
                    "rejected_image_url": pending_url,
                    "rejected_prompt": pending_prompt,
                    "correction": pending_correction,
                    "step_instruction": step.get("instruction", ""),
                    "step_detail": step.get("detail", ""),
                    "image_label": step.get("imageLabel", ""),
                })
                log_editor_decision({
                    "action": "image_rejected_pending",
                    "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                    "category": inferred_category,
                    "step_id": request.step_id,
                    "rejected_image_url": pending_url,
                })
                assess_and_record_image_quality(
                    image_url=pending_url,
                    local_path=local_static_path_for_url(pending_url) or "",
                    context={
                        "source": "repair_editor_rejection",
                        "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                        "category": inferred_category,
                        "step_id": request.step_id,
                        "correction": pending_correction,
                        "editor_rejected": True,
                    },
                )
                image_repair_example(
                    "rejected",
                    manifest,
                    step,
                    before_image_url=step.get("imageUrl", ""),
                    after_image_url=pending_url,
                    correction=pending_correction,
                )
                save_walkthrough(manifest.get("walkthrough_id") or slugify(request.walkthrough_id), manifest)
                return {"status": "discarded_pending", "walkthrough": manifest}

            previous = step.get("previousImageUrl")
            if previous:
                current = step.get("imageUrl", "")
                step["imageUrl"] = previous
                step["previousImageUrl"] = current
                inferred_category = infer_construction_category(
                    walkthrough_id=request.walkthrough_id,
                    title=manifest.get("title", ""),
                    query=manifest.get("query", ""),
                )
                log_correction_memory({
                    "action": "image_reverted",
                    "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                    "category": inferred_category,
                    "step_id": request.step_id,
                    "restored_image_url": previous,
                    "replaced_image_url": current,
                    "step_instruction": step.get("instruction", ""),
                    "step_detail": step.get("detail", ""),
                    "image_label": step.get("imageLabel", ""),
                })
                log_editor_decision({
                    "action": "image_reverted",
                    "walkthrough_id": manifest.get("walkthrough_id") or request.walkthrough_id,
                    "category": inferred_category,
                    "step_id": request.step_id,
                    "restored_image_url": previous,
                    "replaced_image_url": current,
                })
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


def should_rebuild_cached_walkthrough(manifest: dict | None, force_refresh: bool = False) -> bool:
    if not manifest:
        return False
    if manifest.get("review_status") == "approved":
        return False
    if force_refresh:
        return True
    try:
        cached_schema = int(manifest.get("generator_schema_version") or 0)
    except Exception:
        cached_schema = 0
    return cached_schema < GENERATOR_SCHEMA_VERSION


@app.post("/walkthrough")
def get_walkthrough(
    request: WalkthroughRequest,
    http_request: Request
):
    start_time = time.time()
    taxonomy_match = classify_taxonomy_query(request.query)
    canonical_query = request.query
    canonical_walkthrough_id = query_to_walkthrough_id(request.query)

    if taxonomy_match.get("status") == "matched":
        canonical_query = taxonomy_match.get("canonical_query") or request.query
        canonical_walkthrough_id = taxonomy_match.get("walkthrough_id") or query_to_walkthrough_id(canonical_query)

    cached = load_walkthrough_by_id(canonical_walkthrough_id)
    if not cached:
        cached = load_walkthrough(canonical_query)
    if should_rebuild_cached_walkthrough(cached, request.force_refresh):
        cached = None

    client_ip = client_ip_from_request(http_request)
    user_agent = user_agent_from_request(http_request)

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
            log_visitor_event(
                event="walkthrough_cache_hit",
                query=request.query,
                walkthrough_id=cached.get("walkthrough_id", ""),
                path="/walkthrough",
                time_spent_seconds=round(elapsed_ms / 1000, 2),
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={
                    "cache_hit": True,
                    "taxonomy_match": taxonomy_match,
                    "canonical_query": canonical_query,
                    "canonical_walkthrough_id": canonical_walkthrough_id,
                }
            )
        except Exception as e:
            print("Query logging failed:", e)

        return cached

    generated = generate_placeholder_walkthrough(canonical_query)
    generated["walkthrough_id"] = canonical_walkthrough_id
    generated["query"] = canonical_query
    generated.setdefault("aliases", [])
    add_manifest_alias(generated, request.query)
    if canonical_query != request.query:
        add_manifest_alias(generated, canonical_query)
    generated["taxonomy_match"] = taxonomy_match

    save_walkthrough(canonical_walkthrough_id, generated)

    elapsed_ms = int((time.time() - start_time) * 1000)
    latency_warning = elapsed_ms > 60000

    try:
        log_query_event(
            query=request.query,
            walkthrough_id=generated.get("walkthrough_id", ""),
            cache_hit=False,
            response_time_ms=elapsed_ms,
            ip_address=client_ip,
            user_agent=user_agent
        )
        log_visitor_event(
            event="walkthrough_generated",
            query=request.query,
            walkthrough_id=generated.get("walkthrough_id", ""),
            path="/walkthrough",
            time_spent_seconds=round(elapsed_ms / 1000, 2),
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={
                "cache_hit": False,
                "taxonomy_match": taxonomy_match,
                "canonical_query": canonical_query,
                "canonical_walkthrough_id": canonical_walkthrough_id,
                "latency_warning": latency_warning,
            }
        )
    except Exception as e:
        print("Query logging failed:", e)

    if latency_warning:
        generated["latency_warning"] = {
            "threshold_seconds": 60,
            "response_time_seconds": round(elapsed_ms / 1000, 2),
            "message": "Uncached generation exceeded the operational latency target.",
        }

    return generated
