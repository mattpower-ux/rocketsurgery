from pathlib import Path
import json

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


IMAGE_DIR = BASE_DIR / "images"

REGISTRY_PATH = BASE_DIR / "image-registry.json"


def build_image_registry():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    for path in sorted(IMAGE_DIR.glob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix not in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
            continue

        filename = path.name

        records.append({
            "filename": filename,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "suffix": suffix
        })

    registry = {
        "status": "ok",
        "image_count": len(records),
        "images": records
    }

    REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2)
    )

    return registry


def load_image_registry():
    if not REGISTRY_PATH.exists():
        return build_image_registry()

    try:
        return json.loads(
            REGISTRY_PATH.read_text()
        )
    except Exception:
        return build_image_registry()
