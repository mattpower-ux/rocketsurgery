import os
import sys
from pathlib import Path


os.environ.setdefault("OPENAI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import generator
from app.quality_rules import infer_construction_category
from app.step_sequence_validator import validate_and_repair_step_sequence


def test_nonconstruction_categories_and_order():
    assert infer_construction_category(query="repair a windshield chip") == "auto_glass"
    assert infer_construction_category(query="clean cloudy headlights") == "auto_lighting"
    assert infer_construction_category(query="repair lanai screen") == "screen_enclosure"
    steps = [{"title": title} for title in ["Inspect lens", "Clean lens", "Sand lens", "Polish lens"]]
    result = validate_and_repair_step_sequence("clean cloudy headlights", steps)
    assert [step["title"] for step in result["steps"]] == [step["title"] for step in steps]
    assert result["status"] == "passed_unranked_category"


def test_curated_walkthrough_has_asset_sheet_before_steps():
    calls = []
    originals = {
        name: getattr(generator, name)
        for name in (
            "generate_installation_steps_with_research",
            "plan_visual_assets",
            "generate_visual_asset_sheet",
            "generate_step_image_from_asset_sheet",
        )
    }
    try:
        generator.generate_installation_steps_with_research = lambda query, context: [
            {"title": "Inspect", "instruction": "Inspect the lens.", "detail": "Check for oxidation."},
            {"title": "Polish", "instruction": "Polish the lens.", "detail": "Use the selected kit."},
        ]
        generator.plan_visual_assets = lambda query, steps, category: {
            "primary_object": "same cloudy left headlamp on a silver sedan",
            "product": "same clear polycarbonate lens",
            "environment": "same silver sedan hood and black grille",
            "worker": "same worker with visible facial features",
            "tools": ["headlamp restoration kit"],
            "views": ["front", "three-quarter"],
            "locked_prompt": "same silver sedan and left headlamp across every step",
        }
        generator.generate_visual_asset_sheet = lambda brief, key: (
            calls.append(("asset_sheet", brief)) or "https://example.com/sheet.png"
        )
        generator.generate_step_image_from_asset_sheet = lambda prompt, index, asset_sheet_url="", return_metadata=False, allow_text_fallback=True: (
            calls.append(("step_image", index, asset_sheet_url, return_metadata, allow_text_fallback))
            or {"image_url": f"https://example.com/{index}.png", "generation_mode": "asset_sheet_edit"}
        )
        research = {
            "status": "curated_video_metadata",
            "brief": {"required_steps": ["Inspect", "Polish"]},
            "sources": [{"url": "https://www.youtube.com/watch?v=UEJbKLZ7RmM", "transcript_used": False}],
        }
        result = generator.generate_placeholder_walkthrough(
            "How do I restore cloudy headlights?", source_research_override=research
        )
    finally:
        for name, original in originals.items():
            setattr(generator, name, original)

    assert calls[0][0] == "asset_sheet"
    assert all(item[0] == "step_image" and item[2] == "https://example.com/sheet.png" for item in calls[1:])
    assert all(item[3] and not item[4] for item in calls[1:])
    assert result["visual_assets"]["primary_object"].startswith("same cloudy left headlamp")
    assert result["source_research"]["sources"] == research["sources"]
    assert result["generator_schema_version"] == generator.GENERATOR_SCHEMA_VERSION


if __name__ == "__main__":
    test_nonconstruction_categories_and_order()
    test_curated_walkthrough_has_asset_sheet_before_steps()
    print("new walkthrough generation tests passed")
