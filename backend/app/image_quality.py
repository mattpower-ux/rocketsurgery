import json
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR

try:
    from app.metadata_repository import metadata_repository
except ImportError:
    from metadata_repository import metadata_repository


IMAGE_QA_DIR = BASE_DIR / "image-qa"
IMAGE_QA_INDEX = IMAGE_QA_DIR / "image-quality-index.json"
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MIN_APPROVED_BYTES = 25_000


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_image_quality_index() -> dict:
    if not IMAGE_QA_INDEX.exists():
        return {"schema_version": 1, "updated_at": "", "records": {}}

    try:
        data = json.loads(IMAGE_QA_INDEX.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("schema_version", 1)
    data.setdefault("updated_at", "")
    data.setdefault("records", {})
    return data


def save_image_quality_index(index: dict) -> dict:
    IMAGE_QA_DIR.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = now_iso()
    IMAGE_QA_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def image_key(image_url: str) -> str:
    parsed = urlparse(image_url or "")
    return Path(parsed.path).name or (image_url or "unknown")


def assess_image_quality(
    image_url: str,
    local_path: str | Path = "",
    context: dict | None = None,
) -> dict:
    context = context or {}
    path = Path(local_path) if local_path else None
    suffix = path.suffix.lower() if path else Path(urlparse(image_url or "").path).suffix.lower()
    exists = bool(path and path.exists())
    size_bytes = path.stat().st_size if exists else 0

    issues = []
    if suffix not in ALLOWED_SUFFIXES:
        issues.append("unsupported_file_type")
    if path and not exists:
        issues.append("file_missing")
    if exists and suffix != ".svg" and size_bytes < MIN_APPROVED_BYTES:
        issues.append("image_file_too_small")

    prompt = " ".join([
        str(context.get("query", "")),
        str(context.get("step_instruction", "")),
        str(context.get("image_label", "")),
        str(context.get("image_prompt", "")),
    ]).lower()
    filename = image_key(image_url).lower()

    prompt_tokens = [
        token
        for token in prompt.replace("-", " ").split()
        if len(token) >= 5 and token.isalnum()
    ]
    overlap = [token for token in prompt_tokens[:40] if token in filename]

    if prompt_tokens and not overlap and context.get("require_filename_overlap", False):
        issues.append("filename_has_no_prompt_overlap")

    status = "approved_for_review" if not issues else "needs_review"
    if context.get("editor_accepted"):
        status = "editor_accepted_with_warnings" if issues else "editor_accepted"
    if context.get("editor_rejected"):
        status = "editor_rejected"

    return {
        "image_url": image_url,
        "image_key": image_key(image_url),
        "local_path": str(path) if path else "",
        "status": status,
        "issues": issues,
        "suffix": suffix,
        "exists": exists,
        "size_bytes": size_bytes,
        "context": context,
        "checked_at": now_iso(),
    }


def record_image_quality(record: dict) -> dict:
    index = load_image_quality_index()
    record_id = record.get("image_key") or image_key(record.get("image_url", ""))
    index["records"][record_id] = record
    save_image_quality_index(index)
    metadata_repository.upsert_record("image_quality", record_id, record)
    return record


def assess_and_record_image_quality(
    image_url: str,
    local_path: str | Path = "",
    context: dict | None = None,
) -> dict:
    return record_image_quality(
        assess_image_quality(
            image_url=image_url,
            local_path=local_path,
            context=context,
        )
    )
