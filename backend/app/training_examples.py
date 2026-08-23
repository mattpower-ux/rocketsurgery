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


def _step_signature(step: dict) -> dict:
    return {
        "id": step.get("id"),
        "image_label": step.get("imageLabel", ""),
        "instruction": step.get("instruction", ""),
        "detail": step.get("detail", ""),
    }


def _step_key(step: dict) -> str:
    return " | ".join([
        str(step.get("imageLabel", "")),
        str(step.get("instruction", "")),
        str(step.get("detail", "")),
    ]).strip().lower()


def compare_walkthrough_steps(before_steps: list[dict], after_steps: list[dict]) -> dict:
    before_order = [_step_key(step) for step in before_steps or []]
    after_order = [_step_key(step) for step in after_steps or []]
    changed_steps = []

    for index, after_step in enumerate(after_steps or []):
        before_step = (before_steps or [])[index] if index < len(before_steps or []) else {}
        changed_fields = [
            field for field in ["imageLabel", "instruction", "detail", "imagePrompt"]
            if str(before_step.get(field, "")) != str(after_step.get(field, ""))
        ]
        if changed_fields:
            changed_steps.append({
                "position": index + 1,
                "step_id": after_step.get("id"),
                "changed_fields": changed_fields,
                "before": _step_signature(before_step),
                "after": _step_signature(after_step),
            })

    return {
        "before_step_count": len(before_steps or []),
        "after_step_count": len(after_steps or []),
        "step_order_changed": before_order != after_order,
        "before_step_order": [_step_signature(step) for step in before_steps or []],
        "after_step_order": [_step_signature(step) for step in after_steps or []],
        "changed_steps": changed_steps,
    }


def walkthrough_edit_example(action: str, before: dict, after: dict, context: dict | None = None) -> dict:
    before = before or {}
    after = after or {}
    context = context or {}
    step_delta = compare_walkthrough_steps(before.get("steps", []) or [], after.get("steps", []) or [])

    return append_training_example(
        "walkthrough_edit",
        {
            "action": action,
            "walkthrough_id": after.get("walkthrough_id") or before.get("walkthrough_id", ""),
            "query": after.get("query") or before.get("query", ""),
            "title": after.get("title") or before.get("title", ""),
            "before_review_status": before.get("review_status", ""),
            "after_review_status": after.get("review_status", ""),
            "before_quality_status": before.get("quality_status", ""),
            "after_quality_status": after.get("quality_status", ""),
            **step_delta,
            "context": context,
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
