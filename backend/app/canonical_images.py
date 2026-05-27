from pathlib import Path

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify


CANONICAL_IMAGE_DIR = BASE_DIR / "canonical-images"

API_BASE_URL = "https://rocketsurgery-api.onrender.com"


CANONICAL_STEP_IMAGE_SETS = {
    "replace toilet": [
        "replace-toilet-step-001.webp",
        "replace-toilet-step-002.webp",
        "replace-toilet-step-003.webp",
        "replace-toilet-step-004.webp",
        "replace-toilet-step-005.webp"
    ],
    "replace kitchen faucet": [
        "replace-kitchen-faucet-step-001.webp",
        "replace-kitchen-faucet-step-002.webp",
        "replace-kitchen-faucet-step-003.webp",
        "replace-kitchen-faucet-step-004.webp",
        "replace-kitchen-faucet-step-005.webp"
    ],
    "install dishwasher": [
        "install-dishwasher-step-001.webp",
        "install-dishwasher-step-002.webp",
        "install-dishwasher-step-003.webp",
        "install-dishwasher-step-004.webp",
        "install-dishwasher-step-005.webp"
    ],
    "install bidet": [
        "install-bidet-step-001.webp",
        "install-bidet-step-002.webp",
        "install-bidet-step-003.webp",
        "install-bidet-step-004.webp",
        "install-bidet-step-005.webp"
    ]
}


def ensure_canonical_image_storage():
    CANONICAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_canonical_key(query: str) -> str:
    q = query.lower().strip()

    for key in CANONICAL_STEP_IMAGE_SETS.keys():
        if key in q:
            return key

    if "toilet" in q:
        return "replace toilet"

    if "faucet" in q:
        return "replace kitchen faucet"

    if "dishwasher" in q:
        return "install dishwasher"

    if "bidet" in q:
        return "install bidet"

    return ""


def get_canonical_image_urls(query: str) -> list[str]:
    ensure_canonical_image_storage()

    key = get_canonical_key(query)

    if not key:
        return []

    filenames = CANONICAL_STEP_IMAGE_SETS.get(key, [])

    urls = []

    for filename in filenames:
        path = CANONICAL_IMAGE_DIR / filename

        if path.exists():
            urls.append(
                f"{API_BASE_URL}/static/canonical-images/{filename}"
            )

    return urls


def canonical_image_status():
    ensure_canonical_image_storage()

    sets = []

    for key, filenames in CANONICAL_STEP_IMAGE_SETS.items():
        available = []

        for filename in filenames:
            path = CANONICAL_IMAGE_DIR / filename

            available.append({
                "filename": filename,
                "exists": path.exists(),
                "url": f"{API_BASE_URL}/static/canonical-images/{filename}"
            })

        sets.append({
            "canonical_key": key,
            "slug": slugify(key),
            "expected_count": len(filenames),
            "available_count": len([
                item for item in available
                if item["exists"]
            ]),
            "images": available
        })

    return {
        "status": "canonical image storage ready",
        "canonical_image_dir": str(CANONICAL_IMAGE_DIR),
        "sets": sets
    }
