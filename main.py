"""
Application Duplicate Detector — entry point.

Usage:
    python main.py

Responsibilities:
  1. Configure rotating file logging
  2. Ensure required directories exist
  3. Install dependencies check
  4. Launch the Tk UI
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# ── Make sure we're running from the project root ────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import cfg


# ── Logging setup ─────────────────────────────────────────────────────────────

def _setup_logging():
    log_path = cfg.log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, cfg.get("logging", "level", default="INFO").upper(), logging.INFO)
    max_bytes = cfg.get("logging", "max_bytes", default=5_242_880)
    backup_count = cfg.get("logging", "backup_count", default=3)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  —  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(fh)

    # Console handler (INFO+ only)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s  %(name)s — %(message)s"))
    root_logger.addHandler(ch)


# ── Dependency check ──────────────────────────────────────────────────────────

def _check_dependencies():
    missing = []
    try:
        import send2trash  # noqa: F401
    except ImportError:
        missing.append("send2trash")

    if missing:
        print(
            f"\n⚠  Missing dependencies: {', '.join(missing)}\n"
            f"   Run:  pip install {' '.join(missing)}\n\n"
            "   The app will start but safe removal will NOT work until "
            "send2trash is installed.\n"
        )


# ── Bootstrap required directories ───────────────────────────────────────────

def _ensure_dirs():
    for d in [cfg.db_path.parent, cfg.log_path.parent, cfg.reports_dir]:
        d.mkdir(parents=True, exist_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    _setup_logging()
    _ensure_dirs()
    _check_dependencies()

    logger = logging.getLogger(__name__)
    logger.info("=== Application Duplicate Detector starting ===")

    try:
        from app.ui.app import AppWindow
        app = AppWindow()
        app.mainloop()
    except Exception:
        logger.exception("Fatal error — application crashed")
        raise
    finally:
        logger.info("=== Application exiting ===")


if __name__ == "__main__":
    main()
