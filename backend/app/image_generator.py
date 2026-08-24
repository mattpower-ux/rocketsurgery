import base64
import os
from pathlib import Path

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


def generate_step_image(query: str, step_number: int = 1) -> str:
    ensure_storage()

    safe_query = slugify(query) or "walkthrough"
    filename = f"{safe_query}-step-{step_number:03d}.png"
    output_path = IMAGES_DIR / filename

    if output_path.exists():
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
        },
    )
