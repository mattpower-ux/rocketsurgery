try:
    from app.storage import query_to_walkthrough_id
except ImportError:
    from storage import query_to_walkthrough_id

try:
    from app.image_generator import generate_step_image
except ImportError:
    from image_generator import generate_step_image

try:
    from app.step_planner import generate_installation_steps_with_research
except ImportError:
    from step_planner import generate_installation_steps_with_research

try:
    from app.labor_estimator import estimate_labor_minutes
except ImportError:
    from labor_estimator import estimate_labor_minutes

try:
    from app.canonical_images import get_canonical_image_urls
except ImportError:
    from canonical_images import get_canonical_image_urls

try:
    from app.step_sequence_validator import validate_and_repair_step_sequence
except ImportError:
    from step_sequence_validator import validate_and_repair_step_sequence

try:
    from app.quality_rules import format_rules_for_prompt, infer_construction_category
except ImportError:
    from quality_rules import format_rules_for_prompt, infer_construction_category

try:
    from app.taxonomy_router import classify_taxonomy_query
except ImportError:
    from taxonomy_router import classify_taxonomy_query

try:
    from app.source_research import (
        discover_source_research,
        format_research_for_image_prompt,
        format_research_for_planner,
    )
except ImportError:
    from source_research import (
        discover_source_research,
        format_research_for_image_prompt,
        format_research_for_planner,
    )


MAX_GENERATION_QUERY_LENGTH = 160
MAX_IMAGE_PROMPT_LENGTH = 900
GENERATOR_SCHEMA_VERSION = 4


CHIMNEY_CAP_STEPS = [
    {
        "title": "Confirm Cap Fit and Gather Tools",
        "instruction": "Confirm the chimney cap matches the flue and collect installation tools.",
        "detail": "Have the cap, tape measure, drill or screwdriver, masonry bits if needed, fasteners or clamp hardware, gloves, and exterior-rated sealant ready before going onto the roof.",
    },
    {
        "title": "Access Chimney Safely",
        "instruction": "Set the ladder securely and reach the chimney crown.",
        "detail": "Place the ladder on stable ground, maintain safe roof access, and keep tools controlled while moving to the chimney.",
    },
    {
        "title": "Inspect Crown and Flue",
        "instruction": "Check the chimney crown, flue tile, and surrounding masonry.",
        "detail": "Look for cracks, loose mortar, blocked flue openings, or damaged crown surfaces that should be repaired before the cap is installed.",
    },
    {
        "title": "Clean Chimney Crown",
        "instruction": "Brush debris from the chimney crown and flue edge.",
        "detail": "Remove leaves, loose grit, old sealant, and soot from the mounting area so the cap sits flat and secure.",
    },
    {
        "title": "Dry-Fit Chimney Cap",
        "instruction": "Set the cap over the flue and confirm alignment.",
        "detail": "Center the cap over the flue opening with even overhang and verify the mesh clears the flue tile without blocking draft.",
    },
    {
        "title": "Mark and Drill Fastener Points",
        "instruction": "Mark the attachment points and drill pilot holes if required.",
        "detail": "Use the cap base or clamp holes as guides, then drill carefully into the crown or masonry only where the cap hardware requires it.",
    },
    {
        "title": "Secure Chimney Cap",
        "instruction": "Fasten the chimney cap to the flue or crown.",
        "detail": "Tighten screws, clamps, or anchors evenly so the cap is stable, level, and not deforming the flue tile or mesh.",
    },
    {
        "title": "Seal and Inspect Installation",
        "instruction": "Seal required fastener points and inspect the completed cap.",
        "detail": "Apply exterior-rated sealant only where appropriate, then verify the cap is centered, secure, weather-shedding, and clear of the flue opening.",
    },
]


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


def build_visual_template(query: str, category: str = "") -> str:
    clean_query = (query or "").lower()
    if category == "chimney_cap" or "chimney cap" in clean_query:
        return (
            "same residential brick chimney on a gray shingle roof, same rectangular clay flue tile and concrete chimney crown, "
            "same stainless steel chimney cap with mesh sides and flat overhanging lid, same worker in tan work shirt, gloves, and roof-safe footwear"
        )
    return (
        "same primary product or fixture, same surrounding installation setting, same material colors, "
        "same perspective, and same recurring worker character style across every step"
    )


def build_visual_continuity_prompt(visual_template: str) -> str:
    return (
        "Walkthrough visual continuity contract: all steps must depict the same primary object, same product shape, "
        "same surrounding setting, and same recurring worker style unless the step explicitly replaces or removes that object. "
        f"Locked visual template: {visual_template}."
    )


def planned_steps_for_category(query: str, category: str, research_context: str = "") -> list[dict]:
    if category == "chimney_cap":
        return [dict(step) for step in CHIMNEY_CAP_STEPS]
    return generate_installation_steps_with_research(query, research_context)


def generate_placeholder_walkthrough(query: str) -> dict:
    clean_query = safe_task_text(query)
    taxonomy_match = classify_taxonomy_query(clean_query)
    if taxonomy_match.get("status") == "matched":
        clean_query = safe_task_text(taxonomy_match.get("canonical_query") or clean_query)
        walkthrough_id = taxonomy_match.get("walkthrough_id") or query_to_walkthrough_id(clean_query)
    else:
        walkthrough_id = query_to_walkthrough_id(clean_query)

    source_research = discover_source_research(clean_query)
    research_context = format_research_for_planner(source_research)
    research_image_prompt = format_research_for_image_prompt(source_research)

    initial_category = infer_construction_category(query=clean_query)
    planned_steps = planned_steps_for_category(clean_query, initial_category, research_context)
    sequence_validation = validate_and_repair_step_sequence(clean_query, planned_steps)
    planned_steps = sequence_validation["steps"]
    category = sequence_validation["category"]
    learned_rule_prompt = format_rules_for_prompt(category)
    visual_template = build_visual_template(clean_query, category)
    visual_continuity_prompt = build_visual_continuity_prompt(visual_template)

    labor = estimate_labor_minutes(
        query=clean_query,
        step_count=len(planned_steps)
    )

    canonical_images = get_canonical_image_urls(clean_query)

    steps = []

    for index, planned_step in enumerate(planned_steps[:8], start=1):

        image_prompt = safe_image_prompt(
            f"{clean_query} - {planned_step.get('title', f'Step {index}')}. "
            f"{visual_continuity_prompt} {learned_rule_prompt} {research_image_prompt}"
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
        "query": clean_query,
        "aliases": [query] if query != clean_query else [],
        "taxonomy_match": taxonomy_match,
        "walkthrough_type": "generic_foundation",
        "title": f"PLANNED WALKTHROUGH: {clean_query}",
        "generator_schema_version": GENERATOR_SCHEMA_VERSION,
        "visual_template": visual_template,
        "review_status": "draft",
        "quality_status": "order_validated",
        "version": 1,
        "step_sequence_validation": {
            "status": sequence_validation["status"],
            "category": sequence_validation["category"],
            "issues": sequence_validation["issues"],
            "learned_rules_applied": bool(learned_rule_prompt),
            "source_research_applied": bool(research_context or research_image_prompt),
        },
        "source_research": {
            "status": source_research.get("status", ""),
            "researched_at": source_research.get("researched_at", ""),
            "source_types": source_research.get("source_types", []),
            "source_candidate_count": source_research.get("source_candidate_count", 0),
            "brief": source_research.get("brief", {}),
        },
        "disclaimer": "Draft walkthrough only. Manufacturer instructions and local codes must be verified.",
        "estimated_labor_minutes": labor["estimated_labor_minutes"],
        "estimated_labor_label": labor["estimated_labor_label"],
        "steps": steps
    }
