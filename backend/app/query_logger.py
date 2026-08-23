import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

try:
    from app.storage import BASE_DIR
except ImportError:
    from storage import BASE_DIR


LOG_DIR = BASE_DIR / "logs"
LOCAL_QUERY_LOG = LOG_DIR / "query-log.csv"
LOCAL_VISITOR_LOG = LOG_DIR / "visitor-log.csv"

HEADERS = [
    "timestamp",
    "query",
    "brand",
    "model",
    "category",
    "install_mode",
    "region",
    "ip_address",
    "user_agent",
    "walkthrough_id",
    "cache_hit",
    "response_time_ms"
]

VISITOR_HEADERS = [
    "timestamp",
    "event",
    "query",
    "walkthrough_id",
    "path",
    "time_spent_seconds",
    "ip_address",
    "user_agent",
    "metadata"
]


def ensure_local_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not LOCAL_QUERY_LOG.exists():
        with LOCAL_QUERY_LOG.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)


def append_local(row):
    ensure_local_log()

    with LOCAL_QUERY_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([row.get(header, "") for header in HEADERS])


def ensure_visitor_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not LOCAL_VISITOR_LOG.exists():
        with LOCAL_VISITOR_LOG.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(VISITOR_HEADERS)


def append_visitor_local(row):
    ensure_visitor_log()

    with LOCAL_VISITOR_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([row.get(header, "") for header in VISITOR_HEADERS])


def _parse_timestamp(value: str):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _date_in_range(value: str, start_date: str = "", end_date: str = "") -> bool:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return True

    event_date = parsed.date()

    if start_date:
        try:
            if event_date < datetime.fromisoformat(start_date).date():
                return False
        except ValueError:
            pass

    if end_date:
        try:
            if event_date > datetime.fromisoformat(end_date).date():
                return False
        except ValueError:
            pass

    return True


def _read_visitor_rows(limit: int = 250, start_date: str = "", end_date: str = ""):
    ensure_visitor_log()

    with LOCAL_VISITOR_LOG.open("r", newline="", encoding="utf-8") as f:
        rows = [
            row
            for row in csv.DictReader(f)
            if _date_in_range(row.get("timestamp", ""), start_date, end_date)
        ]

    if limit and limit > 0:
        rows = rows[-limit:]

    rows.reverse()
    return rows


def _visitor_summary(rows: list[dict]):
    unique_ips = {
        row.get("ip_address", "").strip()
        for row in rows
        if row.get("ip_address", "").strip()
    }

    total_time_spent_seconds = 0
    walkthrough_events = 0

    for row in rows:
        try:
            total_time_spent_seconds += float(row.get("time_spent_seconds") or 0)
        except ValueError:
            pass

        if row.get("query") or row.get("walkthrough_id"):
            walkthrough_events += 1

    return {
        "event_count": len(rows),
        "walkthrough_event_count": walkthrough_events,
        "unique_ip_count": len(unique_ips),
        "total_time_spent_seconds": round(total_time_spent_seconds, 2)
    }


def append_google_sheet(row):
    if os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() != "true":
        return {"status": "disabled"}

    if gspread is None or Credentials is None:
        return {"status": "missing_dependencies"}

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    service_account_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "/data/google-service-account.json"
    )

    if not sheet_id or not Path(service_account_path).exists():
        return {"status": "missing_config"}

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    credentials = Credentials.from_service_account_file(
        service_account_path,
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    sheet_name = os.getenv(
        "GOOGLE_SHEET_TAB",
        "Sheet1"
    )

    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)

    sheet.append_row(
        [row.get(header, "") for header in HEADERS],
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS"
    )

    return {"status": "logged"}


def log_query_event(
    query: str,
    brand: str = "",
    model: str = "",
    category: str = "",
    install_mode: str = "",
    region: str = "",
    ip_address: str = "",
    user_agent: str = "",
    walkthrough_id: str = "",
    cache_hit: bool = False,
    response_time_ms: int | float = 0
):
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "brand": brand,
        "model": model,
        "category": category,
        "install_mode": install_mode,
        "region": region,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "walkthrough_id": walkthrough_id,
        "cache_hit": str(bool(cache_hit)).lower(),
        "response_time_ms": int(response_time_ms or 0)
    }

    append_local(row)

    try:
        sheet_result = append_google_sheet(row)
    except Exception as e:
        sheet_result = {
            "status": "sheet_error",
            "error": str(e)
        }

    return {
        "status": "logged_locally",
        "sheet": sheet_result,
        "row": row
    }


def log_visitor_event(
    event: str,
    query: str = "",
    walkthrough_id: str = "",
    path: str = "",
    time_spent_seconds: int | float = 0,
    ip_address: str = "",
    user_agent: str = "",
    metadata: dict | None = None
):
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": (event or "client_event").strip()[:80],
        "query": query or "",
        "walkthrough_id": walkthrough_id or "",
        "path": path or "",
        "time_spent_seconds": round(float(time_spent_seconds or 0), 2),
        "ip_address": ip_address or "",
        "user_agent": user_agent or "",
        "metadata": json.dumps(metadata or {}, ensure_ascii=False)
    }

    append_visitor_local(row)

    return {
        "status": "logged_locally",
        "row": row
    }


def list_visitor_events(limit: int = 250, start_date: str = "", end_date: str = ""):
    rows = _read_visitor_rows(limit=limit, start_date=start_date, end_date=end_date)

    return {
        "status": "ok",
        "summary": _visitor_summary(rows),
        "visitors": rows,
        "filters": {
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date
        }
    }


def visitor_events_csv(start_date: str = "", end_date: str = ""):
    rows = _read_visitor_rows(limit=0, start_date=start_date, end_date=end_date)
    return rows
