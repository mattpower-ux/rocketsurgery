import os
import time
import traceback
from datetime import datetime, timezone

try:
    from app.admin import process_bulk_queries
except ImportError:
    from admin import process_bulk_queries


WORKER_SLEEP_SECONDS = int(
    os.getenv("WORKER_SLEEP_SECONDS", "30")
)

WORKER_ERROR_SLEEP_SECONDS = int(
    os.getenv("WORKER_ERROR_SLEEP_SECONDS", "120")
)

WORKER_LIMIT_PER_LOOP = int(
    os.getenv("WORKER_LIMIT_PER_LOOP", "1")
)


def log(message: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[RocketSurgery worker] {timestamp} {message}", flush=True)


def run_worker():
    log("Worker started.")

    while True:
        try:
            result = process_bulk_queries(
                limit=WORKER_LIMIT_PER_LOOP
            )

            processed = result.get("processed_count", 0)
            failed = result.get("failed_count", 0)
            remaining = result.get("remaining_queued", 0)

            log(
                f"Processed={processed} Failed={failed} Remaining={remaining}"
            )

            if processed == 0 and remaining == 0:
                log(
                    f"No queued jobs. Sleeping {WORKER_SLEEP_SECONDS}s."
                )
                time.sleep(WORKER_SLEEP_SECONDS)
                continue

            time.sleep(WORKER_SLEEP_SECONDS)

        except Exception as e:
            log(f"Worker error: {e}")
            traceback.print_exc()
            time.sleep(WORKER_ERROR_SLEEP_SECONDS)


if __name__ == "__main__":
    run_worker()
