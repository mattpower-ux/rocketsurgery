import os
import sys
from pathlib import Path


os.environ.setdefault("OPENAI_API_KEY", "test-key")

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app import generator


def test_asset_sheet_first_generation():
    calls = []

    def fake_asset_sheet(description, asset_key="visual-assets"):
        calls.append(("asset_sheet", asset_key, description))
        return "https://rocketsurgery-api.onrender.com/static/images/test-asset-sheet.png"

    def fake_step_image(prompt, step_number=1, asset_sheet_url="", cache_key_suffix=""):
        calls.append(("step_image", step_number, asset_sheet_url, prompt))
        return f"https://rocketsurgery-api.onrender.com/static/images/test-step-{step_number}.png"

    original_asset_sheet = generator.generate_visual_asset_sheet
    original_step_image = generator.generate_step_image_from_asset_sheet
    original_research = generator.discover_source_research
    original_step_planner = generator.generate_installation_steps_with_research

    try:
        generator.generate_visual_asset_sheet = fake_asset_sheet
        generator.generate_step_image_from_asset_sheet = fake_step_image
        generator.discover_source_research = lambda query: {"status": "skipped_test"}
        generator.generate_installation_steps_with_research = lambda query, context: [
            {
                "title": "Prepare Area",
                "instruction": "Prepare the work area.",
                "detail": "Clear the area and gather tools.",
            },
            {
                "title": "Install Fixture",
                "instruction": "Install the fixture.",
                "detail": "Set the fixture in place and secure it.",
            },
        ]

        walkthrough = generator.generate_placeholder_walkthrough("How do I install attic insulation?")
    finally:
        generator.generate_visual_asset_sheet = original_asset_sheet
        generator.generate_step_image_from_asset_sheet = original_step_image
        generator.discover_source_research = original_research
        generator.generate_installation_steps_with_research = original_step_planner

    assert calls[0][0] == "asset_sheet"
    assert all(call[0] == "step_image" for call in calls[1:])
    assert all(call[2].endswith("/test-asset-sheet.png") for call in calls[1:])
    assert walkthrough["image_generation_pipeline"]["requires_asset_sheet_before_step_images"] is True
    assert walkthrough["image_generation_pipeline"]["step_image_generation_mode"] == "asset_sheet_reference"
    assert all(step["imageGenerationMode"] == "asset_sheet_reference" for step in walkthrough["steps"])
    assert all(step["imageUrl"] for step in walkthrough["steps"])


if __name__ == "__main__":
    test_asset_sheet_first_generation()
    print("asset-sheet-first generation test passed")
