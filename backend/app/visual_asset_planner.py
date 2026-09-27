import json
import os

from openai import OpenAI


SYSTEM_PROMPT = """Design one locked visual reference for an illustrated how-to walkthrough.
Return only a JSON object with these string fields: primary_object, product,
environment, worker, locked_prompt; and these arrays of strings: tools, views.

Rules:
- Choose ONE specific, coherent physical setup for the whole walkthrough.
- In primary_object, state the object's shape, color, material, and exact installed
  location on its parent car, appliance, wall, roof, frame, or fixture. A label
  like "car headlight lens" is insufficient.
- Name recurring surroundings and colors. Include tools actually used in the steps.
- Describe the same human character, with recognizable facial features when visible.
- For replacement, show the old and new item as distinct labeled states while keeping
  the surrounding setting fixed. Otherwise never introduce an alternate model.
- The reference sheet must show the same item from useful angles before step images.
- Do not invent product brands or technical specifications.
- The locked_prompt is a complete visual identity contract of 180-700 characters,
  not a narration, a list of steps, or an image-generation command. End at a sentence.
- Honor any supplied visual guidance, including left/right orientation and colors.
- Keep every value concise and directly drawable. No markdown or extra keys.
"""


CATEGORY_SCENE_GUARDS = {
    "screen_enclosure": (
        "One fixed screen bay in a multi-panel lanai or pool enclosure, with adjacent framed bays "
        "and part of the screened roof visible. Never depict a hinged screen door, door handle, "
        "or solid-wall doorway as the target panel."
    ),
    "auto_lighting": (
        "The same headlamp lens remains mounted in the same vehicle's front headlamp housing "
        "in every view; never show a detached lens."
    ),
    "auto_glass": (
        "The target is the same front windshield on one vehicle, never a side window or loose pane."
    ),
}


def plan_visual_assets(query: str, steps: list[dict], category: str, visual_guidance: str = "") -> dict:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    context = {
        "query": query,
        "category": category,
        "visual_guidance": visual_guidance,
        "mandatory_scene": CATEGORY_SCENE_GUARDS.get(category, ""),
        "steps": [
            {"title": step.get("title", ""), "instruction": step.get("instruction", "")}
            for step in steps[:8]
        ],
    }
    required = ("primary_object", "product", "environment", "worker", "locked_prompt")
    for attempt in range(2):
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({**context, "retry": attempt > 0})},
            ],
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        if (
            all(isinstance(raw.get(key), str) and raw[key].strip() for key in required)
            and len(raw["primary_object"].strip()) >= 45
            and len(raw["product"].strip()) >= 30
            and len(raw["environment"].strip()) >= 35
            and 100 <= len(raw["locked_prompt"].strip()) <= 700
            and all(isinstance(raw.get(key), list) and raw[key] for key in ("tools", "views"))
        ):
            break
    else:
        raise ValueError("Visual asset plan lacks a concrete installed-object anchor")

    worker = raw["worker"].strip()
    if "face" not in worker.lower() and "facial" not in worker.lower():
        worker += "; consistent illustrated facial features when visible"
    scene_guard = CATEGORY_SCENE_GUARDS.get(category, "")
    return {
        **{key: raw[key].strip() for key in required if key != "worker"},
        "worker": worker,
        "locked_prompt": f"{raw['locked_prompt'].strip()} {scene_guard}".strip(),
        "tools": [str(item).strip()[:100] for item in raw["tools"][:10] if str(item).strip()],
        "views": [str(item).strip()[:100] for item in raw["views"][:6] if str(item).strip()],
    }
