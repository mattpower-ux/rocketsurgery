import json
import time
from pathlib import Path

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR


TRAINING_DIR = BASE_DIR / "training-examples"
TRAINING_EXAMPLES_FILE = TRAINING_DIR / "editor-training-examples.jsonl"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_training_example(example_type: str, payload: dict) -> dict:
    record = {
        "schema_version": 1,
        "example_type": example_type,
        "created_at": now_iso(),
        **(payload or {}),
    }
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    with TRAINING_EXAMPLES_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def image_repair_example(
    action: str,
    walkthrough: dict,
    step: dict,
    before_image_url: str = "",
    after_image_url: str = "",
    correction: str = "",
) -> dict:
    return append_training_example(
        "image_repair",
        {
            "action": action,
            "walkthrough_id": walkthrough.get("walkthrough_id", ""),
            "query": walkthrough.get("query", ""),
            "title": walkthrough.get("title", ""),
            "step_id": step.get("id"),
            "step_instruction": step.get("instruction", ""),
            "step_detail": step.get("detail", ""),
            "image_label": step.get("imageLabel", ""),
            "image_prompt": step.get("imagePrompt", ""),
            "before_image_url": before_image_url,
            "after_image_url": after_image_url,
            "correction": correction,
        },
    )


def product_photo_example(action: str, category: str, brand: str, model: str, payload: dict) -> dict:
    return append_training_example(
        "product_photo",
        {
            "action": action,
            "category": category,
            "brand": brand,
            "model": model,
            **(payload or {}),
        },
    )
