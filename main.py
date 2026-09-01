"""
Main launcher for IADCS (Intelligent Application Deduplication & Categorization System).
Supports both CLI mode and Desktop UI mode.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import cfg


def _setup_logging():
    log_path = cfg.log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, cfg.get("logging", "level", default="INFO").upper(), logging.INFO)
    max_bytes = cfg.get("logging", "max_bytes", default=5_242_880)
    backup_count = cfg.get("logging", "backup_count", default=3)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  —  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s  %(name)s — %(message)s"))
    root_logger.addHandler(ch)


def _ensure_dirs():
    for d in [cfg.db_path.parent, cfg.log_path.parent, cfg.reports_dir]:
        d.mkdir(parents=True, exist_ok=True)


def main():
    _setup_logging()
    _ensure_dirs()

    logger = logging.getLogger(__name__)
    logger.info("=== IADCS Starting ===")

    # If subcommands are passed or --help/--version, run CLI
    cli_commands = {"scan", "duplicates", "categories", "rules", "report", "remove", "--help", "-h", "-v", "--version"}
    if len(sys.argv) > 1 and (sys.argv[1] in cli_commands or sys.argv[1].startswith("-")):
        from app.cli import run_cli
        run_cli()
        return

    try:
        from app.ui.app import AppWindow
        app = AppWindow()
        app.mainloop()
    except Exception as e:
        logger.warning("Tk GUI launch failed (%s), attempting PyQt GUI fallback", e)
        try:
            from app.ui.app_window import launch_gui
            launch_gui()
        except Exception:
            logger.exception("Fatal error launching GUI")
            raise


if __name__ == "__main__":
    main()
