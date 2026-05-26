try:
    from app.storage import query_to_walkthrough_id
except ImportError:
    from storage import query_to_walkthrough_id

try:
    from app.image_generator import generate_step_image
except ImportError:
    from image_generator import generate_step_image


def build_walkthrough_from_specs(query: str, specs: dict) -> dict:
    walkthrough_id = query_to_walkthrough_id(query)

    product_name = specs.get("product_name") or query
    manufacturer = specs.get("manufacturer") or "Unknown manufacturer"
    sequence = specs.get("installation_sequence") or []

    steps = []

    for index, item in enumerate(sequence[:10], start=1):
        title = item.get("step_title") or f"Step {index}"
        instruction = item.get("instruction") or "Complete this installation step."
        source_page = item.get("source_page")

        image_prompt = (
            f"{manufacturer} {product_name} installation. "
            f"{title}. {instruction}. "
            "Use only the visible installation action described. "
            "Technical field manual illustration."
        )

        image_url = generate_step_image(image_prompt, index)

        steps.append(
            {
                "id": index,
                "instruction": instruction,
                "detail": f"Source page: {source_page}" if source_page else "Verify against manufacturer manual.",
                "imageLabel": f"Step {index}: {title}",
                "imageUrl": image_url,
                "hotspots": [
                    {
                        "id": f"step-{index}-spec",
                        "label": "Spec check",
                        "title": "Manufacturer Spec",
                        "content": build_hotspot_content(specs, source_page)
                    }
                ]
            }
        )

    if not steps:
        steps = [
            {
                "id": 1,
                "instruction": "Review the manufacturer manual before installation.",
                "detail": "No clear installation sequence was extracted.",
                "imageLabel": "Step 1: Review manual",
                "imageUrl": generate_step_image(f"{query} review manufacturer manual", 1),
                "hotspots": [
                    {
                        "id": "manual-review",
                        "label": "Manual",
                        "title": "Manual Review",
                        "content": "The uploaded manual did not provide a clearly extractable installation sequence."
                    }
                ]
            }
        ]

    return {
        "walkthrough_id": walkthrough_id,
        "title": f"MANUAL-GROUNDED WALKTHROUGH: {product_name}",
        "manufacturer": manufacturer,
        "disclaimer": "Based on extracted manufacturer manual text. Local codes and AHJ requirements may vary.",
        "source_summary": {
            "product_name": product_name,
            "manufacturer": manufacturer,
            "installation_type": specs.get("installation_type"),
            "fasteners": specs.get("fasteners"),
            "spacing": specs.get("spacing"),
            "clearances": specs.get("clearances"),
            "overlaps": specs.get("overlaps"),
            "sealants": specs.get("sealants"),
            "tools": specs.get("tools"),
            "warnings": specs.get("warnings")
        },
        "steps": steps
    }


def build_hotspot_content(specs: dict, source_page=None) -> str:
    parts = []

    for key in ["fasteners", "spacing", "clearances", "overlaps", "sealants"]:
        value = specs.get(key)

        if value:
            parts.append(f"{key.title()}: {value}")

    if source_page:
        parts.append(f"Source page: {source_page}")

    if not parts:
        return "No specific manufacturer spec was extracted for this step."

    return " | ".join(str(part) for part in parts)
