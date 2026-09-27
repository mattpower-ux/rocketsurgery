import json
import os

from openai import OpenAI


SYSTEM_PROMPT = """Design one locked visual reference for an illustrated how-to walkthrough.
Return only a JSON object with these string fields: primary_object, product,
environment, worker, locked_prompt; and these arrays of strings: tools, views.

Rules:
- Choose ONE specific, coherent physical setup for the whole walkthrough.
- State the object's shape, size/proportions, color, material, and installed location.
- Name recurring surroundings and colors. Include tools actually used in the steps.
- Describe the same human character, with recognizable facial features when visible.
- For replacement, show the old and new item as distinct labeled states while keeping
  the surrounding setting fixed. Otherwise never introduce an alternate model.
- The reference sheet must show the same item from useful angles before step images.
- Do not invent product brands or technical specifications.
- Keep every value concise and directly drawable. No markdown or extra keys.
"""


def plan_visual_assets(query: str, steps: list[dict], category: str) -> dict:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({
                    "query": query,
                    "category": category,
                    "steps": [
                        {"title": step.get("title", ""), "instruction": step.get("instruction", "")}
                        for step in steps[:8]
                    ],
                }),
            },
        ],
    )
    raw = json.loads(response.choices[0].message.content or "{}")
    required = ("primary_object", "product", "environment", "worker", "locked_prompt")
    if not all(isinstance(raw.get(key), str) and raw[key].strip() for key in required):
        raise ValueError("Visual asset plan is missing a concrete locked description")
    if not all(isinstance(raw.get(key), list) and raw[key] for key in ("tools", "views")):
        raise ValueError("Visual asset plan is missing tools or views")
    return {
        **{key: raw[key].strip()[:500] for key in required},
        "tools": [str(item).strip()[:100] for item in raw["tools"][:10] if str(item).strip()],
        "views": [str(item).strip()[:100] for item in raw["views"][:6] if str(item).strip()],
    }
