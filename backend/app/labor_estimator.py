CATEGORY_BASE_MINUTES = {
    "toilets": 90,
    "faucets": 75,
    "kitchen faucets": 75,
    "bidets": 90,
    "dishwashers": 120,
    "refrigerators": 45,
    "induction ranges": 90,
    "heat pump water heaters": 240,
    "tankless water heaters": 240,
    "water softeners": 150,
    "ventilation fans": 120,
    "energy recovery ventilators": 240,
    "siding": 480,
    "trim": 240,
    "roofing": 480,
    "metal roofing": 480,
    "composite decking": 480,
    "flooring": 300,
    "tile": 480,
    "smart thermostats": 45,
    "smart switches": 45,
    "home battery storage": 360,
    "solar panels": 480,
}


def estimate_labor_minutes(query: str, category: str = "", step_count: int = 0):
    q = (query or "").lower()
    c = (category or "").lower()

    base = 90

    for key, minutes in CATEGORY_BASE_MINUTES.items():
        if key in q or key in c:
            base = minutes
            break

    if step_count:
        base = max(base, step_count * 12)

    low = max(15, int(base * 0.75))
    high = int(base * 1.35)

    return {
        "estimated_labor_minutes": base,
        "estimated_labor_label": f"Estimated labor: {low}–{high} minutes"
    }
