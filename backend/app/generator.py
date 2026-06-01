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

try:
    from app.labor_estimator import estimate_labor_minutes
except ImportError:
    from labor_estimator import estimate_labor_minutes

try:
    from app.canonical_images import get_canonical_image_urls
except ImportError:
    from canonical_images import get_canonical_image_urls


MAX_GENERATION_QUERY_LENGTH = 160
MAX_IMAGE_PROMPT_LENGTH = 420


def safe_task_text(text: str, max_len: int = MAX_GENERATION_QUERY_LENGTH) -> str:
    text = " ".join((text or "").split())
    if not text:
        return "Untitled installation walkthrough"
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip(" ,;:-")


def safe_image_prompt(text: str) -> str:
    prompt = " ".join((text or "").split())

    # Reduce false moderation hits from ambiguous short construction phrases.
    prompt = prompt.replace("house wrap", "weather-resistive wall barrier")
    prompt = prompt.replace("House wrap", "weather-resistive wall barrier")

    base = (
        "Professional construction training illustration. "
        "Show a safe residential building installation step with realistic materials, "
        "clear tool placement, no injuries, no weapons, no illegal activity. "
    )
    prompt = f"{base}{prompt}"
    if len(prompt) > MAX_IMAGE_PROMPT_LENGTH:
        prompt = prompt[:MAX_IMAGE_PROMPT_LENGTH].rstrip(" ,;:-")
    return prompt


def generate_placeholder_walkthrough(query: str) -> dict:
    clean_query = safe_task_text(query)
    walkthrough_id = query_to_walkthrough_id(clean_query)

    planned_steps = generate_installation_steps(clean_query)

    labor = estimate_labor_minutes(
        query=clean_query,
        step_count=len(planned_steps)
    )

    canonical_images = get_canonical_image_urls(clean_query)

    steps = []

    for index, planned_step in enumerate(planned_steps[:8], start=1):

        image_prompt = safe_image_prompt(
            f"{clean_query} — {planned_step.get('title', f'Step {index}')}"
        )

        if index - 1 < len(canonical_images):
            image_url = canonical_images[index - 1]
        else:
            image_url = generate_step_image(
                image_prompt,
                index
            )

        steps.append(
            {
                "id": index,
                "instruction": planned_step.get("instruction", "Complete this installation step."),
                "detail": planned_step.get("detail", "Follow manufacturer instructions and local code requirements."),
                "imageLabel": f"Step {index}: {planned_step.get('title', 'Installation step')}",
                "imagePrompt": image_prompt,
                "imageUrl": image_url,
                "imageRepairHistory": [],
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
        "estimated_labor_minutes": labor["estimated_labor_minutes"],
        "estimated_labor_label": labor["estimated_labor_label"],
        "steps": steps
    }
