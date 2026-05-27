from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

try:
    from app.canonical_images import CANONICAL_IMAGE_DIR
except ImportError:
    from canonical_images import CANONICAL_IMAGE_DIR

try:
    from app.storage import load_walkthrough, save_walkthrough
except ImportError:
    from storage import load_walkthrough, save_walkthrough

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
        save_bulk_catalog_requests
    )
except ImportError:
    from admin import (
        admin_status,
        save_bulk_queries,
        save_catalog_request,
        process_bulk_queries,
        save_bulk_catalog_requests
    )


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
    return process_bulk_queries(limit=limit)


@app.post("/admin/process-model-discovery")
def post_process_model_discovery(limit: int = 5):
    return process_model_discovery(limit=limit)


@app.post("/admin/seed-canonical-walkthroughs")
def post_seed_canonical_walkthroughs():
    return seed_canonical_walkthroughs()


@app.post("/walkthrough")
def get_walkthrough(request: WalkthroughRequest):
    cached = load_walkthrough(request.query)

    if cached:
        return cached

    generated = generate_placeholder_walkthrough(request.query)

    save_walkthrough(generated["walkthrough_id"], generated)

    return generated
