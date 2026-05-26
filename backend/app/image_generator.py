import base64
import os
from pathlib import Path

from openai import OpenAI

try:
    from app.storage import IMAGES_DIR, slugify, ensure_storage
except ImportError:
    from storage import IMAGES_DIR, slugify, ensure_storage


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

API_BASE_URL = "https://rocketsurgery-api.onrender.com"


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


def generate_step_image(query: str, step_number: int = 1) -> str:
    ensure_storage()

    safe_query = slugify(query) or "walkthrough"
    filename = f"{safe_query}-step-{step_number:03d}.png"
    output_path = IMAGES_DIR / filename

    if output_path.exists():
        return f"{API_BASE_URL}/static/images/{filename}"

    prompt = build_image_prompt(query, f"Step {step_number}")

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    output_path.write_bytes(image_bytes)

    return f"{API_BASE_URL}/static/images/{filename}"
