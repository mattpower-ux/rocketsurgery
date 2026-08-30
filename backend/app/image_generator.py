import base64
import os
from pathlib import Path
import time
from urllib.parse import urlparse

from openai import OpenAI

try:
    from app.storage import IMAGES_DIR, slugify, ensure_storage
except ImportError:
    from storage import IMAGES_DIR, slugify, ensure_storage

try:
    from app.config import API_BASE_URL
except ImportError:
    from config import API_BASE_URL

try:
    from app.image_quality import assess_and_record_image_quality
except ImportError:
    from image_quality import assess_and_record_image_quality


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def build_image_prompt(query: str, step_label: str = "Step 1") -> str:
    return f"""
Create a high-quality technical installation illustration for RocketSurgery.

Topic: {query}
Panel: {step_label}

The image should look like a polished app-ready construction walkthrough panel, similar to a premium illustrated field manual or contractor training comic.

Visual style:
- clean semi-realistic technical illustration
- crisp black outlines with subtle shading
- accurate construction materials and tool details
- realistic wood grain, fasteners, siding, flashing, pipe, wire, roof, or product components when relevant
- light jobsite background, not cluttered
- modern mobile app illustration quality
- clear focal point
- strong depth and perspective
- professional instructional graphic, not cartoonish
- high-resolution polished rendering
- limited but realistic color palette
- red arrows or red dashed circles may be used to highlight the action
- blue circular hotspot markers may appear where specs could be tapped

Composition requirements:
- show exactly one installation action or concept
- make the work area large and readable on a phone screen
- use arrows, callouts, cutaway details, or magnified inset circles only where helpful
- avoid tiny labels or unreadable text
- avoid brand logos and copyrighted marks
- avoid messy backgrounds
- avoid photorealistic people or faces
- avoid surreal, decorative, or fantasy imagery

Output goal:
A crisp, clear, contractor-friendly instructional panel that could appear inside the RocketSurgery mobile app.
"""


def build_asset_sheet_prompt(description: str) -> str:
    return f"""
Create a RocketSurgery visual asset reference sheet for a contractor walkthrough.

Asset brief:
{description}

The sheet must show the reusable visual components before any step narration:
- primary product/object from front, side, and top/three-quarter angles
- important subparts and fasteners as separate callouts
- surrounding installation environment
- recurring worker/character design
- tools and materials lineup

Visual style:
- clean semi-realistic technical illustration
- consistent proportions across all views
- crisp black outlines with subtle shading
- neutral background, no decorative clutter
- no brand logos, no tiny unreadable labels
- mobile-app-ready construction training style

Output goal:
A single approved asset sheet that later step images can use as the locked visual bible.
"""


def write_generated_image(prompt: str, filename: str, context: dict) -> str:
    ensure_storage()
    output_path = IMAGES_DIR / filename

    if output_path.exists():
        image_url = f"{API_BASE_URL}/static/images/{filename}"
        assess_and_record_image_quality(
            image_url=image_url,
            local_path=output_path,
            context={**context, "source": f"{context.get('source', 'generated_image')}_cache_hit"},
        )
        return image_url

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    output_path.write_bytes(image_bytes)

    image_url = f"{API_BASE_URL}/static/images/{filename}"
    assess_and_record_image_quality(
        image_url=image_url,
        local_path=output_path,
        context=context,
    )
    return image_url


def write_image_response(result, filename: str, context: dict) -> str:
    ensure_storage()
    output_path = IMAGES_DIR / filename
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    output_path.write_bytes(image_bytes)

    image_url = f"{API_BASE_URL}/static/images/{filename}"
    assess_and_record_image_quality(
        image_url=image_url,
        local_path=output_path,
        context=context,
    )
    return image_url


def local_static_image_path(url: str) -> Path | None:
    parsed_path = urlparse(url or "").path
    prefix = "/static/images/"
    if not parsed_path.startswith(prefix):
        return None
    relative = parsed_path[len(prefix):].lstrip("/")
    path = IMAGES_DIR / relative
    return path if path.exists() else None


def generate_visual_asset_sheet(description: str, asset_key: str = "visual-assets") -> str:
    safe_key = slugify(asset_key) or "visual-assets"
    filename = f"{safe_key}-asset-sheet.png"
    prompt = build_asset_sheet_prompt(description)
    return write_generated_image(
        prompt,
        filename,
        {
            "source": "generated_visual_asset_sheet",
            "asset_key": safe_key,
            "asset_prompt": description,
        },
    )


def generate_step_image(query: str, step_number: int = 1, cache_key_suffix: str = "") -> str:
    ensure_storage()

    safe_query = slugify(query) or "walkthrough"
    suffix = f"-{slugify(cache_key_suffix)}" if cache_key_suffix else ""
    filename = f"{safe_query}{suffix}-step-{step_number:03d}.png"
    output_path = IMAGES_DIR / filename

    if output_path.exists() and not cache_key_suffix:
        image_url = f"{API_BASE_URL}/static/images/{filename}"
        assess_and_record_image_quality(
            image_url=image_url,
            local_path=output_path,
            context={
                "source": "image_cache_hit",
                "image_prompt": query,
                "step_number": step_number,
            },
        )
        return image_url

    prompt = build_image_prompt(query, f"Step {step_number}")
    return write_generated_image(
        prompt,
        filename,
        {
            "source": "generated_step_image",
            "image_prompt": query,
            "step_number": step_number,
            "cache_key_suffix": cache_key_suffix,
        },
    )


def generate_step_image_from_asset_sheet(query: str, step_number: int = 1, asset_sheet_url: str = "", cache_key_suffix: str = "") -> str:
    reference_path = local_static_image_path(asset_sheet_url)
    if not reference_path:
        return generate_step_image(query, step_number, cache_key_suffix=cache_key_suffix)

    ensure_storage()
    safe_query = slugify(query) or "walkthrough"
    suffix = slugify(cache_key_suffix) or str(int(time.time()))
    filename = f"{safe_query}-asset-ref-{suffix}-step-{step_number:03d}.png"
    output_path = IMAGES_DIR / filename

    if output_path.exists():
        return f"{API_BASE_URL}/static/images/{filename}"

    prompt = build_image_prompt(
        (
            f"{query}\n\n"
            "Use the provided asset sheet image as the controlling visual reference. "
            "Preserve the same product/object geometry, material colors, environment, worker design, tool shapes, and proportions from the asset sheet. "
            "Do not invent a different model, color, setting, or character. "
            "Create only the requested step panel, changing pose, crop, tool placement, action highlight, and camera angle as needed while keeping the locked assets recognizable."
        ),
        f"Step {step_number}",
    )
    with reference_path.open("rb") as reference_image:
        result = client.images.edit(
            model="gpt-image-1",
            image=[reference_image],
            prompt=prompt,
            size="1024x1024",
            input_fidelity="high",
            response_format="b64_json",
        )

    return write_image_response(
        result,
        filename,
        {
            "source": "generated_step_image_from_asset_sheet",
            "image_prompt": query,
            "step_number": step_number,
            "asset_sheet_url": asset_sheet_url,
            "cache_key_suffix": cache_key_suffix,
        },
    )
