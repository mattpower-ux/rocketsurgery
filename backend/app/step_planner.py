import json
import os

from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You create concise contractor installation walkthroughs.

Rules:
- Return ONLY valid JSON
- No markdown
- No explanations
- No prose outside JSON

Generate sequential installation steps.

Each step must contain:
- title
- instruction
- detail

Requirements:
- contractor-focused
- concise
- one action per step
- visually illustratable
- mobile-friendly
- avoid unnecessary words
- avoid safety/legal disclaimers
- avoid conversational tone

Return this format:

[
  {
    "title": "...",
    "instruction": "...",
    "detail": "..."
  }
]
"""


def generate_installation_steps(query: str):
    return generate_installation_steps_with_research(query)


def generate_installation_steps_with_research(query: str, research_context: str = ""):
    user_content = f"Create a contractor walkthrough for: {query}"
    if research_context:
        user_content += (
            "\n\nBackground research signals to use for accuracy. "
            "Do not cite or quote these; convert them into original steps:\n"
            f"{research_context}"
        )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)

        if isinstance(parsed, list):
            return parsed

    except Exception:
        pass

    return [
        {
            "title": "Prepare work area",
            "instruction": "Verify materials and installation conditions.",
            "detail": "Confirm product compatibility and jobsite readiness."
        },
        {
            "title": "Perform installation",
            "instruction": "Complete the installation sequence carefully.",
            "detail": "Follow manufacturer instructions and local code requirements."
        }
    ]
