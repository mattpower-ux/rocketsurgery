import json
import re
from datetime import datetime, timezone

try:
    from app.storage import (
        BASE_DIR,
        slugify,
        save_walkthrough
    )
except ImportError:
    from storage import (
        BASE_DIR,
        slugify,
        save_walkthrough
    )

try:
    from app.generator import generate_placeholder_walkthrough
except ImportError:
    from generator import generate_placeholder_walkthrough


ADMIN_DIR = BASE_DIR / "admin"
CATALOG_DIR = BASE_DIR / "catalog"

BULK_QUERIES_FILE = ADMIN_DIR / "bulk-queries.json"
CATALOG_REQUESTS_FILE = CATALOG_DIR / "catalog-requests.json"
PRODUCT_OPTIONS_FILE = CATALOG_DIR / "product-options.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_admin_storage():
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    if not BULK_QUERIES_FILE.exists():
        BULK_QUERIES_FILE.write_text(
            json.dumps({"queries": []}, indent=2),
            encoding="utf-8"
        )

    if not CATALOG_REQUESTS_FILE.exists():
        CATALOG_REQUESTS_FILE.write_text(
            json.dumps({"requests": []}, indent=2),
            encoding="utf-8"
        )


def load_json(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data


MAX_QUERY_LENGTH = 180
MAX_SLUG_LENGTH = 110


CATEGORY_HEADING_PATTERN = re.compile(
    r"^(?:[\W_]*\s*)?(framing|plumbing|electrical|windows|doors|siding|flooring|tiling|structural|fastening|permits)\b.*$",
    re.IGNORECASE
)

KNOWN_TASK_STARTERS = [
    "How to",
    "Drywall taping",
    "Spray foam",
    "Building permit",
]


def shorten_text(text: str, max_len: int = MAX_QUERY_LENGTH) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip(" ,;:-")


def safe_query_slug(query: str) -> str:
    base = slugify(shorten_text(query, MAX_QUERY_LENGTH))
    if len(base) <= MAX_SLUG_LENGTH:
        return base
    return base[:MAX_SLUG_LENGTH].rstrip("-")


def split_concatenated_tasks(text: str) -> list[str]:
    """Turn pasted category lists into one clean job per task.

    This protects the queue from a common paste problem where a formatted list
    loses line breaks and becomes one enormous query, which later creates
    filesystem errors from very long image filenames.
    """
    if not text:
        return []

    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"[🏗️💧🚪🧱🏠]+", "\n", cleaned)

    # Force a line break before known task starters when rich text loses bullets/newlines.
    for starter in KNOWN_TASK_STARTERS:
        cleaned = re.sub(rf"(?<!^)(?={re.escape(starter)}\b)", "\n", cleaned)

    # Also split before category labels embedded in one long line.
    cleaned = re.sub(
        r"(?i)(framing and drywall|plumbing and electrical|windows, doors, and siding|flooring and tiling|structural, fastening, and permits)",
        "\n",
        cleaned,
    )

    candidates = []
    for line in cleaned.splitlines():
        line = re.sub(r"^[\-•*\d\.\)\s]+", "", line).strip()
        line = re.sub(r"\s+", " ", line)
        if not line:
            continue
        if CATEGORY_HEADING_PATTERN.match(line) and not line.lower().startswith("how to"):
            continue
        if len(line) < 6:
            continue
        candidates.append(shorten_text(line))

    # De-duplicate while preserving order.
    seen = set()
    result = []
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def quarantine_bad_bulk_records(bulk: dict) -> int:
    """Move malformed giant queue records out of active processing."""
    changed = 0
    for item in bulk.get("queries", []):
        query = item.get("query", "") or ""
        slug = item.get("query_slug", "") or ""
        if item.get("status") in {"queued", "failed"} and (len(query) > MAX_QUERY_LENGTH or len(slug) > MAX_SLUG_LENGTH):
            item["status"] = "ignored"
            item["ignored_at"] = now_iso()
            item["quarantine_reason"] = "Query was too long and likely came from a pasted category list. Delete it and re-add split tasks."
            changed += 1
    return changed


def save_bulk_queries(raw_text: str):
    ensure_admin_storage()

    lines = split_concatenated_tasks(raw_text)

    existing = load_json(BULK_QUERIES_FILE, {"queries": []})
    quarantine_bad_bulk_records(existing)
    existing_queries = existing.get("queries", [])

    existing_texts = {
        item.get("query", "").lower()
        for item in existing_queries
    }

    added = []

    for line in lines:
        line = shorten_text(line)
        normalized = line.lower()

        if normalized in existing_texts:
            continue

        record = {
            "query": line,
            "query_slug": safe_query_slug(line),
            "status": "queued",
            "attempts": 0,
            "created_at": now_iso()
        }

        existing_queries.append(record)
        existing_texts.add(normalized)
        added.append(record)

    existing["queries"] = existing_queries
    save_json(BULK_QUERIES_FILE, existing)

    return {
        "status": "saved",
        "submitted_count": len(lines),
        "added_count": len(added),
        "duplicate_count": len(lines) - len(added),
        "total_count": len(existing_queries),
        "added": added
    }


def process_bulk_queries(limit: int = 5):
    ensure_admin_storage()

    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    quarantine_bad_bulk_records(bulk)
    queries = bulk.get("queries", [])

    processed = []
    failed = []

    queued = [
        item for item in queries
        if item.get("status") == "queued"
    ]

    for item in queued[:limit]:
        query = shorten_text(item.get("query", ""))
        item["query"] = query
        item["query_slug"] = safe_query_slug(query)
        item["status"] = "processing"
        item["processing_started_at"] = now_iso()
        save_json(BULK_QUERIES_FILE, bulk)

        try:
            item["attempts"] = int(item.get("attempts", 0)) + 1
            item["last_attempt_at"] = now_iso()

            walkthrough = generate_placeholder_walkthrough(query)

            save_walkthrough(
                walkthrough["walkthrough_id"],
                walkthrough
            )

            item["status"] = "completed"
            item["completed_at"] = now_iso()
            item["walkthrough_id"] = walkthrough["walkthrough_id"]

            processed.append({
                "query": query,
                "walkthrough_id": walkthrough["walkthrough_id"]
            })

        except Exception as e:
            item["status"] = "failed"
            item["error"] = str(e)
            item["last_error"] = str(e)
            item["failed_at"] = now_iso()

            failed.append({
                "query": query,
                "error": str(e)
            })

    save_json(BULK_QUERIES_FILE, bulk)

    return {
        "status": "bulk processing complete",
        "processed_count": len(processed),
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
        "remaining_queued": len([
            q for q in queries
            if q.get("status") == "queued"
        ])
    }



def save_bulk_catalog_requests(raw_text: str):
    ensure_admin_storage()

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    added = []
    failed = []

    for line in lines:
        try:
            if "|" not in line:
                failed.append({
                    "line": line,
                    "error": "Missing | separator"
                })
                continue

            brand, category = line.split("|", 1)

            result = save_catalog_request(
                brand=brand.strip(),
                category=category.strip(),
                models_text="",
                discover_top_models=True
            )

            added.append(result["request"])

        except Exception as e:
            failed.append({
                "line": line,
                "error": str(e)
            })

    return {
        "status": "bulk catalog requests processed",
        "submitted_count": len(lines),
        "added_count": len(added),
        "failed_count": len(failed),
        "added": added,
        "failed": failed
    }


def save_catalog_request(
    brand: str,
    category: str,
    models_text: str = "",
    discover_top_models: bool = True
):
    ensure_admin_storage()

    brand = brand.strip()
    category = category.strip()

    models = [
        line.strip()
        for line in models_text.splitlines()
        if line.strip()
    ]

    request_record = {
        "brand": brand,
        "brand_slug": slugify(brand),
        "category": category,
        "category_slug": slugify(category),
        "models": models,
        "discover_top_models": discover_top_models and len(models) == 0,
        "requested_model_count": 10 if discover_top_models and len(models) == 0 else len(models),
        "status": "queued_for_model_discovery" if discover_top_models and len(models) == 0 else "models_supplied",
        "created_at": now_iso()
    }

    requests = load_json(CATALOG_REQUESTS_FILE, {"requests": []})
    requests["requests"].append(request_record)
    save_json(CATALOG_REQUESTS_FILE, requests)

    update_product_options_from_catalog_request(request_record)

    return {
        "status": "saved",
        "request": request_record
    }


def update_product_options_from_catalog_request(request_record: dict):
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})

    category_slug = request_record["category_slug"]
    category_name = request_record["category"]

    if category_slug not in product_options:
        product_options[category_slug] = {
            "keywords": [
                category_name.lower(),
                category_slug.replace("-", " ")
            ],
            "brands": []
        }

    brands = product_options[category_slug].setdefault("brands", [])

    brand_name = request_record["brand"]
    models = request_record.get("models", [])

    existing_brand = None

    for brand_entry in brands:
        if brand_entry.get("brand", "").lower() == brand_name.lower():
            existing_brand = brand_entry
            break

    if existing_brand is None:
        existing_brand = {
            "brand": brand_name,
            "models": []
        }
        brands.append(existing_brand)

    existing_models = {
        model.lower()
        for model in existing_brand.get("models", [])
    }

    for model in models:
        if model.lower() not in existing_models:
            existing_brand["models"].append(model)

    save_json(PRODUCT_OPTIONS_FILE, product_options)

    return product_options


def admin_status():
    ensure_admin_storage()

    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    requests = load_json(CATALOG_REQUESTS_FILE, {"requests": []})
    product_options = load_json(PRODUCT_OPTIONS_FILE, {})

    completed = len([
        q for q in bulk.get("queries", [])
        if q.get("status") == "completed"
    ])

    queued = len([
        q for q in bulk.get("queries", [])
        if q.get("status") == "queued"
    ])

    failed = len([
        q for q in bulk.get("queries", [])
        if q.get("status") == "failed"
    ])

    processing = len([
        q for q in bulk.get("queries", [])
        if q.get("status") == "processing"
    ])

    ignored = len([
        q for q in bulk.get("queries", [])
        if q.get("status") == "ignored"
    ])

    return {
        "status": "admin storage ready",
        "bulk_query_count": len(bulk.get("queries", [])),
        "bulk_completed_count": completed,
        "bulk_queued_count": queued,
        "bulk_processing_count": processing,
        "bulk_failed_count": failed,
        "bulk_ignored_count": ignored,
        "catalog_request_count": len(requests.get("requests", [])),
        "catalog_category_count": len(product_options.keys())
    }


def list_bulk_query_jobs():
    """Return queued, failed, completed, and ignored bulk query records for admin review."""
    ensure_admin_storage()
    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    changed = quarantine_bad_bulk_records(bulk)
    if changed:
        save_json(BULK_QUERIES_FILE, bulk)
    queries = bulk.get("queries", [])

    grouped = {
        "queued": [],
        "processing": [],
        "failed": [],
        "completed": [],
        "ignored": [],
        "all": queries
    }

    for item in queries:
        status = item.get("status", "queued")
        grouped.setdefault(status, []).append(item)

    return {
        "status": "loaded",
        "counts": {
            "all": len(queries),
            "queued": len(grouped.get("queued", [])),
            "processing": len(grouped.get("processing", [])),
            "failed": len(grouped.get("failed", [])),
            "completed": len(grouped.get("completed", [])),
            "ignored": len(grouped.get("ignored", []))
        },
        **grouped
    }


def retry_bulk_query(query_slug: str):
    """Move a failed/completed/ignored bulk query back to queued."""
    ensure_admin_storage()
    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})

    for item in bulk.get("queries", []):
        if item.get("query_slug") == query_slug or safe_query_slug(item.get("query", "")) == query_slug:
            if item.get("status") == "queued":
                return {"status": "already_queued", "job": item}

            item["status"] = "queued"
            item["retried_at"] = now_iso()
            item.pop("error", None)
            item.pop("completed_at", None)
            item.pop("last_error", None)
            item.pop("failed_at", None)
            save_json(BULK_QUERIES_FILE, bulk)
            return {
                "status": "queued",
                "message": "Job was returned to the waiting queue. It will not run until the worker runs or you click Run Now.",
                "job": item
            }

    return {"status": "not_found", "query_slug": query_slug}


def ignore_bulk_query(query_slug: str):
    """Mark a bulk query ignored without deleting its history."""
    ensure_admin_storage()
    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})

    for item in bulk.get("queries", []):
        if item.get("query_slug") == query_slug or safe_query_slug(item.get("query", "")) == query_slug:
            item["status"] = "ignored"
            item["ignored_at"] = now_iso()
            save_json(BULK_QUERIES_FILE, bulk)
            return {"status": "ignored", "job": item}

    return {"status": "not_found", "query_slug": query_slug}


def delete_bulk_query(query_slug: str):
    """Remove a bulk query from the queue file."""
    ensure_admin_storage()
    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    before = len(bulk.get("queries", []))

    bulk["queries"] = [
        item for item in bulk.get("queries", [])
        if item.get("query_slug") != query_slug and safe_query_slug(item.get("query", "")) != query_slug
    ]

    after = len(bulk.get("queries", []))
    save_json(BULK_QUERIES_FILE, bulk)

    return {
        "status": "deleted" if after < before else "not_found",
        "query_slug": query_slug,
        "deleted_count": before - after
    }



def process_specific_bulk_query(query_slug: str):
    """Process one specific queued job immediately.

    This is different from retry_bulk_query(): retry only puts a job back in
    line; this function actually runs generation for the selected job now.
    """
    ensure_admin_storage()
    bulk = load_json(BULK_QUERIES_FILE, {"queries": []})
    quarantine_bad_bulk_records(bulk)

    target = None
    for item in bulk.get("queries", []):
        item_slug = item.get("query_slug") or safe_query_slug(item.get("query", ""))
        if item_slug == query_slug:
            target = item
            break

    if target is None:
        return {
            "status": "not_found",
            "query_slug": query_slug,
            "message": "No matching bulk query job was found."
        }

    if target.get("status") != "queued":
        return {
            "status": "not_queued",
            "query_slug": query_slug,
            "job_status": target.get("status"),
            "message": "This job must be queued before it can be run. Use Retry + Run Now for failed or ignored jobs."
        }

    query = shorten_text(target.get("query", ""))
    target["query"] = query
    target["query_slug"] = safe_query_slug(query)
    target["status"] = "processing"
    target["processing_started_at"] = now_iso()
    save_json(BULK_QUERIES_FILE, bulk)

    try:
        target["attempts"] = int(target.get("attempts", 0)) + 1
        target["last_attempt_at"] = now_iso()

        walkthrough = generate_placeholder_walkthrough(query)

        save_walkthrough(
            walkthrough["walkthrough_id"],
            walkthrough
        )

        target["status"] = "completed"
        target["completed_at"] = now_iso()
        target["walkthrough_id"] = walkthrough["walkthrough_id"]
        target.pop("error", None)
        target.pop("last_error", None)

        save_json(BULK_QUERIES_FILE, bulk)

        return {
            "status": "completed",
            "message": "Job was run immediately and completed.",
            "query": query,
            "walkthrough_id": walkthrough["walkthrough_id"],
            "job": target
        }

    except Exception as e:
        target["status"] = "failed"
        target["error"] = str(e)
        target["last_error"] = str(e)
        target["failed_at"] = now_iso()
        save_json(BULK_QUERIES_FILE, bulk)

        return {
            "status": "failed",
            "message": "Job was run immediately but failed.",
            "query": query,
            "error": str(e),
            "job": target
        }


def retry_and_run_bulk_query(query_slug: str):
    """Queue a selected job, then process that exact job immediately.

    Admin should label this as 'Retry + Run Now' so it is clear that the
    job is not merely returned to the waiting queue.
    """
    retry_result = retry_bulk_query(query_slug)
    if retry_result.get("status") not in {"queued", "already_queued"}:
        return retry_result

    return process_specific_bulk_query(query_slug)


def run_next_bulk_queries(limit: int = 1):
    """Manual admin trigger for processing the next queued jobs.

    This does not start the Render background worker service. It runs queued
    jobs inside the current API request and returns the result.
    """
    try:
        limit = int(limit)
    except Exception:
        limit = 1

    limit = max(1, min(limit, 20))
    return process_bulk_queries(limit=limit)
