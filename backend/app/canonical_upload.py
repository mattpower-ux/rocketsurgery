from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from app.storage import slugify
except ImportError:
    from storage import slugify

try:
    from app.canonical_images import CANONICAL_IMAGE_DIR, API_BASE_URL
except ImportError:
    from canonical_images import CANONICAL_IMAGE_DIR, API_BASE_URL


def save_canonical_image(
    file_bytes: bytes,
    filename: str,
    canonical_key: str,
    step_number: int
):
    CANONICAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    key_slug = slugify(canonical_key)
    step = max(1, int(step_number))

    output_filename = f"{key_slug}-step-{step:03d}.webp"
    output_path = CANONICAL_IMAGE_DIR / output_filename

    temp_suffix = Path(filename).suffix.lower() or ".png"
    temp_path = CANONICAL_IMAGE_DIR / f"_upload-temp-{key_slug}-step-{step:03d}{temp_suffix}"
    temp_path.write_bytes(file_bytes)

    if Image is None:
        temp_path.rename(output_path)
    else:
        with Image.open(temp_path) as img:
            img = img.convert("RGB")
            img.thumbnail((1400, 1400))
            img.save(output_path, "WEBP", quality=82, method=6)

        temp_path.unlink(missing_ok=True)

    return {
        "status": "canonical image saved",
        "canonical_key": canonical_key,
        "step_number": step,
        "filename": output_filename,
        "path": str(output_path),
        "url": f"{API_BASE_URL}/static/canonical-images/{output_filename}"
    }
