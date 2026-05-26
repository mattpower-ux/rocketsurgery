import json
import re
from pathlib import Path

import fitz

try:
    from app.storage import BASE_DIR, slugify
except ImportError:
    from storage import BASE_DIR, slugify


MANUALS_DIR = BASE_DIR / "manuals"
MANUAL_INDEX_FILE = MANUALS_DIR / "manual-index.json"


def ensure_manual_storage():
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)

    if not MANUAL_INDEX_FILE.exists():
        with MANUAL_INDEX_FILE.open("w", encoding="utf-8") as f:
            json.dump({"manuals": []}, f, indent=2)


def load_manual_index():
    ensure_manual_storage()

    with MANUAL_INDEX_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_manual_index(index: dict):
    ensure_manual_storage()

    with MANUAL_INDEX_FILE.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    return index


def manual_storage_status():
    ensure_manual_storage()
    index = load_manual_index()

    return {
        "status": "manual storage ready",
        "manuals_dir": str(MANUALS_DIR),
        "manual_index_file": str(MANUAL_INDEX_FILE),
        "manual_count": len(index.get("manuals", []))
    }


def safe_filename(filename: str) -> str:
    name = Path(filename).stem
    ext = Path(filename).suffix.lower() or ".pdf"
    return f"{slugify(name)}{ext}"


def extract_pdf_text(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages = []

    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        clean_text = re.sub(r"\\s+", " ", text).strip()

        pages.append({
            "page": page_index,
            "text": clean_text
        })

    return {
        "page_count": len(pages),
        "pages": pages
    }


def save_uploaded_manual(file_bytes: bytes, filename: str, manufacturer: str = "unknown"):
    ensure_manual_storage()

    manufacturer_slug = slugify(manufacturer or "unknown")
    folder = MANUALS_DIR / manufacturer_slug
    folder.mkdir(parents=True, exist_ok=True)

    stored_filename = safe_filename(filename)
    pdf_path = folder / stored_filename

    pdf_path.write_bytes(file_bytes)

    extracted = extract_pdf_text(pdf_path)

    text_path = pdf_path.with_suffix(".text.json")
    with text_path.open("w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2)

    index = load_manual_index()

    record = {
        "manufacturer": manufacturer,
        "manufacturer_slug": manufacturer_slug,
        "filename": stored_filename,
        "pdf_path": str(pdf_path),
        "text_path": str(text_path),
        "page_count": extracted["page_count"]
    }

    index["manuals"].append(record)
    save_manual_index(index)

    return {
        "status": "manual uploaded and parsed",
        **record
    }
