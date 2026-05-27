from pathlib import Path
from datetime import datetime, timezone

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


WALKTHROUGHS_DIR = BASE_DIR / "walkthroughs"
IMAGES_DIR = BASE_DIR / "images"


def iso(ts):
    return datetime.fromtimestamp(
        ts,
        tz=timezone.utc
    ).isoformat()


def get_build_status():
    WALKTHROUGHS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    walkthrough_dirs = [
        p for p in WALKTHROUGHS_DIR.iterdir()
        if p.is_dir()
    ]

    image_files = [
        p for p in IMAGES_DIR.iterdir()
        if p.is_file()
    ]

    recent_walkthroughs = sorted(
        walkthrough_dirs,
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:10]

    recent_images = sorted(
        image_files,
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:10]

    latest_activity = 0

    if recent_walkthroughs:
        latest_activity = max(
            latest_activity,
            recent_walkthroughs[0].stat().st_mtime
        )

    if recent_images:
        latest_activity = max(
            latest_activity,
            recent_images[0].stat().st_mtime
        )

    now_ts = datetime.now(timezone.utc).timestamp()

    seconds_since_activity = (
        now_ts - latest_activity
        if latest_activity
        else None
    )

    if seconds_since_activity is None:
        activity_state = "idle"
    elif seconds_since_activity < 120:
        activity_state = "active"
    elif seconds_since_activity < 600:
        activity_state = "slowing"
    else:
        activity_state = "stale"

    return {
        "status": "ok",
        "activity_state": activity_state,
        "seconds_since_activity": seconds_since_activity,
        "walkthrough_count": len(walkthrough_dirs),
        "image_count": len(image_files),
        "recent_walkthroughs": [
            {
                "name": p.name,
                "modified_at": iso(p.stat().st_mtime)
            }
            for p in recent_walkthroughs
        ],
        "recent_images": [
            {
                "name": p.name,
                "modified_at": iso(p.stat().st_mtime)
            }
            for p in recent_images
        ]
    }
