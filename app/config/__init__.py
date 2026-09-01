"""Configuration loader for IADCS."""
from pathlib import Path
from typing import Any, Dict

from app.config.config_loader import cfg

CONFIG_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
DEFAULT_CATEGORIES_FILE = CONFIG_DIR / "default_categories.yaml"


def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            import yaml
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            pass
    return {}


def load_default_categories() -> Dict[str, Any]:
    if DEFAULT_CATEGORIES_FILE.exists():
        try:
            import yaml
            with open(DEFAULT_CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            pass
    return {"categories": []}
