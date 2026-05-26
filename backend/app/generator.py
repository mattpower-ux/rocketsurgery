try:
    from app.storage import query_to_walkthrough_id
except ImportError:
    from storage import query_to_walkthrough_id

try:
    from app.image_generator import generate_step_image
except ImportError:
    from image_generator import generate_step_image


def generate_placeholder_walkthrough(query: str) -> dict:
    walkthrough_id = query_to_walkthrough_id(query)

    clean_query = query.strip() or "Untitled installation walkthrough"

    generated_image_url = generate_step_image(clean_query, 1)

    return {
        "walkthrough_id": walkthrough_id,

        "title": f"AI IMAGE TEST: {clean_query}",

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
                    generated_image_url,

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
                    generated_image_url,

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
                    generated_image_url,

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
