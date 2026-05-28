import csv
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
