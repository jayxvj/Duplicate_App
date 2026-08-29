"""Configuration loader for IADCS."""
from pathlib import Path
from typing import Any, Dict
import yaml

CONFIG_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
DEFAULT_CATEGORIES_FILE = CONFIG_DIR / "default_categories.yaml"


def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_default_categories() -> Dict[str, Any]:
    if DEFAULT_CATEGORIES_FILE.exists():
        with open(DEFAULT_CATEGORIES_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {"categories": []}
