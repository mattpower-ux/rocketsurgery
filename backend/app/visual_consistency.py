import base64
import json
import os

from openai import OpenAI

try:
    from app.image_generator import local_static_image_path
except ImportError:
    from image_generator import local_static_image_path


SYSTEM_PROMPT = """You are a strict visual continuity reviewer for an illustrated how-to app.
Compare the first image (locked asset sheet) with the second image (one step panel).
Return only JSON with boolean same_object, boolean action_visible, and an array
issues containing brief, concrete discrepancies (at most 3).

Check the target object's shape, color, material, placement, parent setting, and
recurring person's appearance. For repair and cleaning, the object must remain
installed. An expected before/after state change is allowed. Reject a panel if
the instructed action is drawn on a nearby grille, bodywork, wall, or other
object instead of the target. Do not reject a useful crop or camera angle change.
Only report discrepancies actually visible in the two images. Do not infer specs.
"""


ASSET_SHEET_PROMPT = """You review a visual asset reference sheet before any how-to step images are generated.
Return only JSON with boolean object_and_setting_match, boolean repeated_views_consistent,
boolean face_is_drawn_if_visible, and an array issues with at most 3 concrete discrepancies.
The sheet must depict the exact object named in the query, in its specified setting.
For repair or cleaning, the object stays installed in its parent setting in every view.
Do not substitute a screen door for a lanai enclosure panel, a loose headlamp for
one installed on a car, or another physical variant. A close-up is okay if the
parent setting remains recognizable. If a person is shown, visible faces need
ordinary illustrated features. Judge the actual image, not just the description.
"""


def assess_asset_sheet(asset_sheet_url: str, query: str, visual_assets: dict) -> dict:
    sheet_path = local_static_image_path(asset_sheet_url)
    if not sheet_path:
        return {"status": "audit_error", "issues": ["Asset sheet unavailable locally"]}
    try:
        encoded = base64.b64encode(sheet_path.read_bytes()).decode("ascii")
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ASSET_SHEET_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": json.dumps({
                        "query": query,
                        "primary_object": visual_assets.get("primary_object", ""),
                        "product": visual_assets.get("product", ""),
                        "environment": visual_assets.get("environment", ""),
                        "worker": visual_assets.get("worker", ""),
                    })},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "high"}},
                ]},
            ],
        )
        result = json.loads(response.choices[0].message.content or "{}")
        checks = ("object_and_setting_match", "repeated_views_consistent", "face_is_drawn_if_visible")
        if not all(isinstance(result.get(key), bool) for key in checks):
            raise ValueError("Incomplete asset sheet review response")
        status = "passed" if all(result[key] for key in checks) else "needs_review"
        return {"status": status, "issues": [str(item)[:220] for item in result.get("issues", [])[:3]]}
    except Exception as exc:
        return {"status": "audit_error", "issues": [str(exc)[:220]]}


def assess_visual_consistency(asset_sheet_url: str, step_image_url: str, action: str, visual_assets: dict) -> dict:
    sheet_path = local_static_image_path(asset_sheet_url)
    step_path = local_static_image_path(step_image_url)
    if not sheet_path or not step_path:
        return {"status": "audit_error", "issues": ["Asset sheet or step image unavailable locally"]}

    def image_part(path):
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "high"}}

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": json.dumps({
                        "target_action": action,
                        "primary_object": visual_assets.get("primary_object", ""),
                        "product": visual_assets.get("product", ""),
                        "environment": visual_assets.get("environment", ""),
                        "locked_prompt": visual_assets.get("locked_prompt", ""),
                    })},
                    image_part(sheet_path),
                    image_part(step_path),
                ]},
            ],
        )
        result = json.loads(response.choices[0].message.content or "{}")
        if not isinstance(result.get("same_object"), bool) or not isinstance(result.get("action_visible"), bool):
            raise ValueError("Incomplete visual review response")
        issues = [str(item)[:220] for item in result.get("issues", [])[:3]]
        status = "passed" if result["same_object"] and result["action_visible"] else "needs_review"
        return {"status": status, "issues": issues}
    except Exception as exc:
        return {"status": "audit_error", "issues": [str(exc)[:220]]}
