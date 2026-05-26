try:
    from app.storage import query_to_walkthrough_id
except ImportError:
    from storage import query_to_walkthrough_id


ROCKETSURGERY_API_URL = "https://rocketsurgery-api.onrender.com"


def render_disk_image_url(filename: str) -> str:
    return f"{ROCKETSURGERY_API_URL}/static/images/{filename}"


def generate_placeholder_walkthrough(query: str) -> dict:
    walkthrough_id = query_to_walkthrough_id(query)

    clean_query = query.strip() or "Untitled installation walkthrough"

    return {
        "walkthrough_id": walkthrough_id,

        "title": f"NEW PLACEHOLDER: {clean_query}",

        "disclaimer":
            "Draft walkthrough only. Manufacturer instructions and local codes must be verified.",

        "steps": [
            {
                "id": 1,

                "instruction":
                    "Identify the exact product and installation condition.",

                "detail":
                    "Confirm manufacturer, model, substrate, exposure, and jobsite conditions before starting.",

                "imageLabel":
                    "Step 1: Confirm product",

                "imageUrl":
                    render_disk_image_url("test-step.svg"),

                "hotspots": [
                    {
                        "id": "product",

                        "label": "Product check",

                        "title": "Product Verification",

                        "content":
                            "Future version will pull this from manufacturer installation manuals."
                    }
                ]
            },

            {
                "id": 2,

                "instruction":
                    "Review the manufacturer installation requirements.",

                "detail":
                    "Fasteners, spacing, clearances, overlaps, and sealants must match the current product guide.",

                "imageLabel":
                    "Step 2: Check manual",

                "imageUrl":
                    render_disk_image_url("test-step.svg"),

                "hotspots": [
                    {
                        "id": "manual",

                        "label": "Manual source",

                        "title": "Manufacturer Manual",

                        "content":
                            "Future version will attach source PDF, page number, and extracted specification."
                    }
                ]
            },

            {
                "id": 3,

                "instruction":
                    "Complete the installation sequence in the correct order.",

                "detail":
                    "The final generated walkthrough will replace this placeholder with product-specific illustrated steps.",

                "imageLabel":
                    "Step 3: Install in sequence",

                "imageUrl":
                    render_disk_image_url("test-step.svg"),

                "hotspots": [
                    {
                        "id": "sequence",

                        "label": "Sequence",

                        "title": "Installation Sequence",

                        "content":
                            "Future version will generate step-by-step visuals and hotspot specs."
                    }
                ]
            }
        ]
    }
