import json
import time
from pathlib import Path

try:
    from app.config import BASE_DIR
except ImportError:
    from config import BASE_DIR


METADATA_DIR = BASE_DIR / "metadata"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class JsonMetadataRepository:
    """Small migration seam for metadata that should eventually live in SQL.

    Runtime assets stay on disk/object storage; this repository is for indexes,
    quality records, lifecycle state, package manifests, and training examples.
    """

    def __init__(self, root: Path = METADATA_DIR):
        self.root = root

    def collection_path(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def load_collection(self, collection: str) -> dict:
        path = self.collection_path(collection)
        if not path.exists():
            return {"schema_version": 1, "updated_at": "", "records": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", 1)
        data.setdefault("updated_at", "")
        data.setdefault("records", {})
        return data

    def save_collection(self, collection: str, data: dict) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = now_iso()
        self.collection_path(collection).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def upsert_record(self, collection: str, record_id: str, record: dict) -> dict:
        data = self.load_collection(collection)
        data["records"][record_id] = {
            **(record or {}),
            "id": record_id,
            "updated_at": now_iso(),
        }
        self.save_collection(collection, data)
        return data["records"][record_id]

    def get_record(self, collection: str, record_id: str) -> dict | None:
        return self.load_collection(collection).get("records", {}).get(record_id)


metadata_repository = JsonMetadataRepository()
