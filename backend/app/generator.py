try:
    from app.storage import query_to_walkthrough_id
except ImportError:
    from storage import query_to_walkthrough_id

try:
    from app.image_generator import generate_step_image
except ImportError:
    from image_generator import generate_step_image

try:
    from app.step_planner import generate_installation_steps
except ImportError:
    from step_planner import generate_installation_steps


def generate_placeholder_walkthrough(query: str) -> dict:
    walkthrough_id = query_to_walkthrough_id(query)
    clean_query = query.strip() or "Untitled installation walkthrough"

    planned_steps = generate_installation_steps(clean_query)

    steps = []

    for index, planned_step in enumerate(planned_steps[:8], start=1):
        image_url = generate_step_image(
            f"{clean_query} — {planned_step.get('title', f'Step {index}')}",
            index
        )

        steps.append(
            {
                "id": index,
                "instruction": planned_step.get("instruction", "Complete this installation step."),
                "detail": planned_step.get("detail", "Follow manufacturer instructions and local code requirements."),
                "imageLabel": f"Step {index}: {planned_step.get('title', 'Installation step')}",
                "imageUrl": image_url,
                "hotspots": [
                    {
                        "id": f"step-{index}-spec",
                        "label": "Spec check",
                        "title": "Specification Check",
                        "content": "Future version will attach manufacturer source, page number, and product-specific spec."
                    }
                ]
            }
        )

    return {
        "walkthrough_id": walkthrough_id,
        "title": f"PLANNED WALKTHROUGH: {clean_query}",
        "disclaimer": "Draft walkthrough only. Manufacturer instructions and local codes must be verified.",
        "steps": steps
    }
