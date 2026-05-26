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
Create a clean technical construction illustration for RocketSurgery.

Topic: {query}
Panel: {step_label}

Style requirements:
- crisp instructional diagram
- simple jobsite construction graphic
- white or light background
- clear outlines
- limited colors
- no photorealism
- no logos
- no brand marks
- no tiny unreadable text
- no decorative art
- show the installation concept clearly
- use arrows/callouts only if visually clear

The image should look like a professional installation manual illustration for a trade contractor using a phone in the field.
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
