from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

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
from fastapi import Request


app = FastAPI(title="RocketSurgery API")

Path("/data/rocketsurgery/images").mkdir(parents=True, exist_ok=True)

app.mount(
    "/static/images",
    StaticFiles(directory="/data/rocketsurgery/images"),
    name="images"
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


class SaveWalkthroughRequest(BaseModel):
    walkthrough: dict




TOILET_PRODUCT_CATALOG = {
    "Kohler": {
        "Highline": {
            "manual_title": "Kohler Highline / Wellworth Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/1004604_2.pdf",
            "models": ["Highline", "Wellworth", "Cimarron"]
        },
        "Wellworth": {
            "manual_title": "Kohler Wellworth / Highline Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/114903_2.pdf",
            "models": ["Highline", "Wellworth", "Cimarron"]
        },
        "Cimarron": {
            "manual_title": "Kohler Toilet Installation Guide",
            "manual_url": "https://resources.kohler.com/onlinecatalog/pdf/1004604_2.pdf",
            "models": ["Highline", "Wellworth", "Cimarron"]
        }
    },
    "Niagara": {
        "Stealth": {
            "manual_title": "Niagara Stealth Toilet Manual",
            "manual_url": "https://niagaracorp.com/wp-content/uploads/2016/10/Stealth_Manual_Final.pdf",
            "models": ["Stealth", "EcoLogic", "Liberty"]
        },
        "EcoLogic": {
            "manual_title": "Niagara EcoLogic / Toilet Manual",
            "manual_url": "https://niagaracorp.com/wp-content/uploads/2016/10/Stealth_Manual_Final.pdf",
            "models": ["Stealth", "EcoLogic", "Liberty"]
        },
        "Liberty": {
            "manual_title": "Niagara Product Resources",
            "manual_url": "https://pro.niagaracorp.com/resources/",
            "models": ["Stealth", "EcoLogic", "Liberty"]
        }
    },
    "American Standard": {
        "Cadet 3": {
            "manual_title": "American Standard Cadet Installation Instructions",
            "manual_url": "https://lixil.cdn.celum.cloud/167930_as_us_bath_install__2467__2876%20%284626%29_0_original.pdf",
            "models": ["Cadet 3", "Champion 4", "Colony"]
        },
        "Champion 4": {
            "manual_title": "American Standard Champion / Toilet Installation Instructions",
            "manual_url": "https://s1.img-b.com/build.com/mediabase/specifications/american_standard/1237308/american-standard-2886.518-b-installation-sheet.pdf",
            "models": ["Cadet 3", "Champion 4", "Colony"]
        },
        "Colony": {
            "manual_title": "American Standard Toilet Installation Instructions",
            "manual_url": "https://lixil.cdn.celum.cloud/167930_as_us_bath_install__2467__2876%20%284626%29_0_original.pdf",
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
            "overlays": []
        }

    base = {
        "status": "loaded",
        "category": "toilet",
        "brand": brand,
        "model": model,
        "manual_title": manual.get("manual_title", "Manufacturer installation guide"),
        "manual_url": manual.get("manual_url", ""),
        "overlays": []
    }

    overlays = []

    # Shared differences that frequently matter versus a generic toilet walkthrough.
    overlays.append({
        "id": "rough-in-check",
        "step_id": 1,
        "x": 58,
        "y": 42,
        "label": "Rough-in check",
        "title": "Verify model rough-in before setting the bowl",
        "content": "Before setting the toilet, confirm the model's rough-in and flange/bolt position against the manufacturer guide. Some models offer 10-inch or 12-inch rough-in variants, and a generic walkthrough may not flag that difference.",
        "type": "model_specific",
        "manual_url": manual.get("manual_url", ""),
        "manual_title": manual.get("manual_title", "Manufacturer installation guide")
    })

    overlays.append({
        "id": "tightening-caution",
        "step_id": 4,
        "x": 52,
        "y": 50,
        "label": "Do not overtighten",
        "title": "Tightening sequence and china protection",
        "content": "Use the model-specific tightening sequence and avoid overtightening tank, bowl, seat, or floor fasteners. Vitreous china can crack if hardware is tightened beyond the manufacturer's instructions.",
        "type": "caution",
        "manual_url": manual.get("manual_url", ""),
        "manual_title": manual.get("manual_title", "Manufacturer installation guide")
    })

    overlays.append({
        "id": "water-level-adjustment",
        "step_id": 6,
        "x": 62,
        "y": 42,
        "label": "Water level",
        "title": "Adjust water level to the model marking",
        "content": "After connecting the supply and test-flushing, adjust the tank water level to the model's marked waterline or valve instructions rather than relying only on generic fill-valve guidance.",
        "type": "adjustment",
        "manual_url": manual.get("manual_url", ""),
        "manual_title": manual.get("manual_title", "Manufacturer installation guide")
    })

    brand_l = brand.lower()
    model_l = model.lower()

    if "niagara" in brand_l or "stealth" in model_l:
        overlays.append({
            "id": "niagara-stealth-components",
            "step_id": 6,
            "x": 42,
            "y": 36,
            "label": "Niagara tank system",
            "title": "Niagara uses model-specific tank components",
            "content": "Niagara Stealth-style toilets use specialized internal tank components. Do not treat internal adjustments as generic flapper-only adjustments; follow the Niagara manual before changing the flush or fill assembly.",
            "type": "model_specific",
            "manual_url": manual.get("manual_url", ""),
            "manual_title": manual.get("manual_title", "Manufacturer installation guide")
        })

    if "american standard" in brand_l or "cadet" in model_l or "champion" in model_l:
        overlays.append({
            "id": "american-standard-ez-install",
            "step_id": 3,
            "x": 50,
            "y": 58,
            "label": "EZ-Install hardware",
            "title": "Use the included mounting hardware sequence",
            "content": "American Standard Cadet/Champion installations may include model-specific EZ-Install hardware. Follow the packaged bolt, gasket, washer, and knob sequence instead of substituting a generic tank-to-bowl order.",
            "type": "model_specific",
            "manual_url": manual.get("manual_url", ""),
            "manual_title": manual.get("manual_title", "Manufacturer installation guide")
        })

    if "kohler" in brand_l:
        overlays.append({
            "id": "kohler-leak-check",
            "step_id": 7,
            "x": 64,
            "y": 52,
            "label": "Kohler leak check",
            "title": "Check connections again after several flushes",
            "content": "Kohler installation guides emphasize flushing several times, checking all connections for leaks, and periodically rechecking after installation. Add this follow-up to the generic completion step.",
            "type": "check",
            "manual_url": manual.get("manual_url", ""),
            "manual_title": manual.get("manual_title", "Manufacturer installation guide")
        })

    base["overlays"] = overlays
    return base

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


@app.post("/admin/save-walkthrough")
def post_save_admin_walkthrough(request: SaveWalkthroughRequest):
    manifest = request.walkthrough or {}
    walkthrough_id = manifest.get("walkthrough_id") or slugify(manifest.get("title", "edited-walkthrough"))

    if not walkthrough_id:
        return {"status": "error", "error": "Missing walkthrough_id"}

    manifest["walkthrough_id"] = walkthrough_id

    steps = manifest.get("steps", []) or []
    normalized_steps = []

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue

        step["id"] = index
        step["imageLabel"] = step.get("imageLabel") or f"Step {index}"
        step["instruction"] = step.get("instruction", "")
        step["detail"] = step.get("detail", "")
        normalized_steps.append(step)

    manifest["steps"] = normalized_steps
    save_walkthrough(walkthrough_id, manifest)

    return {
        "status": "saved",
        "walkthrough_id": walkthrough_id,
        "step_count": len(normalized_steps),
        "walkthrough": manifest
    }


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
