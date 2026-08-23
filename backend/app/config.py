import os
from pathlib import Path


DEFAULT_DATA_DIR = "/data/rocketsurgery"
DEFAULT_API_BASE_URL = "https://rocketsurgery-api.onrender.com"


BASE_DIR = Path(os.getenv("ROCKETSURGERY_DATA_DIR", DEFAULT_DATA_DIR))
API_BASE_URL = os.getenv("ROCKETSURGERY_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
