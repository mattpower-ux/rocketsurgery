import json
from pathlib import Path

from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You extract structured installation facts from manufacturer manuals.

Return ONLY valid JSON.

Do not invent specifications.
If a value is not clearly stated, use null.
Do not include markdown.

Extract:
- product_name
- manufacturer
- installation_type
- fasteners
- spacing
- clearances
- overlaps
- sealants
- tools
- warnings
- installation_sequence

Each installation_sequence item should include:
- step_title
- instruction
- source_page
"""


def load_extracted_manual_text(text_path: str, max_pages: int = 12) -> str:
    path = Path(text_path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data.get("pages", [])[:max_pages]

    chunks = []

    for page in pages:
        chunks.append(
            f"PAGE {page.get('page')}:\n{page.get('text', '')}"
        )

    return "\n\n".join(chunks)


def extract_installation_specs(text_path: str) -> dict:
    manual_text = load_extracted_manual_text(text_path)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": manual_text
            }
        ]
    )

    raw = response.choices[0].message.content

    try:
        return json.loads(raw)
    except Exception:
        return {
            "error": "Could not parse JSON from model",
            "raw": raw
        }
