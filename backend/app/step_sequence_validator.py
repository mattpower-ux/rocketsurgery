try:
    from app.quality_rules import infer_construction_category, category_rules_for
except ImportError:
    from quality_rules import infer_construction_category, category_rules_for


GENERIC_ORDER_RULES = [
    ("shut off", 10),
    ("turn off", 10),
    ("verify power is off", 15),
    ("drain", 20),
    ("disconnect", 30),
    ("remove", 40),
    ("inspect", 50),
    ("clean", 55),
    ("prepare", 60),
    ("measure", 65),
    ("mark", 70),
    ("cut", 80),
    ("install", 90),
    ("position", 95),
    ("connect", 110),
    ("secure", 120),
    ("seal", 130),
    ("test", 150),
    ("verify", 160),
]


CATEGORY_ORDER_RULES = {
    "toilet": [
        ("shut off water", 10),
        ("turn off water", 10),
        ("drain", 20),
        ("disconnect water", 30),
        ("remove bolts", 40),
        ("remove toilet", 50),
        ("remove wax", 60),
        ("inspect flange", 70),
        ("install wax", 80),
        ("set toilet", 90),
        ("connect water", 110),
        ("test", 140),
    ],
    "tile_shower": [
        ("inspect", 10),
        ("prepare", 20),
        ("waterproof", 40),
        ("slope", 50),
        ("set pan", 60),
        ("tile", 90),
        ("grout", 120),
        ("seal", 130),
        ("test", 150),
    ],
    "plumbing_sink": [
        ("shut off water", 10),
        ("verify water", 15),
        ("disconnect supply", 25),
        ("disconnect trap", 30),
        ("disconnect drain", 35),
        ("remove sink", 45),
        ("remove basin", 45),
        ("inspect", 55),
        ("clean", 60),
        ("mount", 75),
        ("install sink", 80),
        ("seal", 95),
        ("connect drain", 110),
        ("connect supply", 120),
        ("leak", 145),
        ("test", 150),
    ],
    "shower_cartridge": [
        ("shut off water", 10),
        ("remove handle", 25),
        ("remove trim", 30),
        ("remove retaining clip", 40),
        ("pull cartridge", 50),
        ("inspect valve body", 60),
        ("lubricate", 70),
        ("install cartridge", 80),
        ("reinstall trim", 105),
        ("turn water", 130),
        ("test", 150),
    ],
    "shower_valve": [
        ("shut off water", 10),
        ("open wall", 20),
        ("expose valve", 30),
        ("cut pipe", 45),
        ("remove valve", 55),
        ("position valve", 70),
        ("connect pipe", 90),
        ("pressure test", 120),
        ("close wall", 140),
        ("test", 150),
    ],
    "prefab_shower": [
        ("shut off water", 10),
        ("remove doors", 20),
        ("disconnect drain", 30),
        ("remove surround", 45),
        ("inspect framing", 55),
        ("level base", 70),
        ("connect drain", 90),
        ("install panels", 100),
        ("seal", 130),
        ("test", 150),
    ],
    "siding": [
        ("inspect", 10),
        ("weather", 20),
        ("flashing", 30),
        ("starter", 40),
        ("install siding", 60),
        ("fasten", 70),
        ("trim", 100),
        ("seal", 120),
    ],
    "chimney_cap": [
        ("gather", 10),
        ("prepare", 10),
        ("access", 20),
        ("ladder", 20),
        ("inspect chimney", 30),
        ("inspect crown", 30),
        ("inspect flue", 30),
        ("clean", 35),
        ("measure", 40),
        ("select", 50),
        ("choose", 50),
        ("dry-fit", 60),
        ("dry fit", 60),
        ("set the cap", 60),
        ("place", 70),
        ("position", 70),
        ("drill", 90),
        ("fasten", 100),
        ("secure", 100),
        ("seal", 120),
        ("verify", 140),
        ("inspect installation", 145),
    ],
}


def step_text(step: dict) -> str:
    return " ".join([
        str(step.get("title", "")),
        str(step.get("instruction", "")),
        str(step.get("detail", "")),
        str(step.get("imageLabel", "")),
    ]).lower()


def rank_step(step: dict, category: str, index: int) -> tuple[int, int]:
    text = step_text(step)
    rules = []
    rules.extend(CATEGORY_ORDER_RULES.get(category, []))

    configured = category_rules_for(category).get("step_order", []) or []
    rules.extend((str(item).lower(), position * 10 + 5) for position, item in enumerate(configured, start=1))

    rules.extend(GENERIC_ORDER_RULES)

    for phrase, rank in rules:
        if phrase in text:
            return rank, index

    return 100, index


def validate_and_repair_step_sequence(query: str, steps: list[dict]) -> dict:
    category = infer_construction_category(query=query)
    original_ids = [step.get("id", index + 1) for index, step in enumerate(steps)]
    ranked = [
        (rank_step(step, category, index), step)
        for index, step in enumerate(steps)
    ]
    repaired_steps = [
        step
        for _, step in sorted(ranked, key=lambda item: item[0])
    ]

    repaired_ids = [step.get("id", index + 1) for index, step in enumerate(repaired_steps)]
    issues = []

    if repaired_ids != original_ids:
        issues.append({
            "type": "step_order_repaired",
            "message": "Steps were reordered before image generation using local prerequisite rules.",
            "original_order": original_ids,
            "repaired_order": repaired_ids,
        })

    for index, step in enumerate(repaired_steps, start=1):
        step["id"] = index

    return {
        "category": category,
        "status": "repaired" if issues else "passed",
        "issues": issues,
        "steps": repaired_steps,
    }
