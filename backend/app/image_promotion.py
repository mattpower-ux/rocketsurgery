from pathlib import Path
import shutil

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify

try:
    from app.image_registry import build_image_registry
except ImportError:
    from image_registry import build_image_registry


IMAGE_DIR = BASE_DIR / "images"
CANONICAL_DIR = BASE_DIR / "canonical-images"


def promote_image_to_canonical(
    filename: str,
    canonical_key: str,
    step_number: int
):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)

    source_path = IMAGE_DIR / filename

    if not source_path.exists():
        return {
            "status": "error",
            "message": f"Image not found: {filename}"
        }

    step = max(1, int(step_number))

    key_slug = slugify(canonical_key)

    extension = source_path.suffix.lower()

    canonical_filename = (
        f"{key_slug}-step-{step:03d}{extension}"
    )

    target_path = CANONICAL_DIR / canonical_filename

    shutil.copy2(source_path, target_path)

    build_image_registry()

    return {
        "status": "promoted",
        "source": str(source_path),
        "target": str(target_path),
        "canonical_key": canonical_key,
        "step_number": step,
        "filename": canonical_filename
    }
