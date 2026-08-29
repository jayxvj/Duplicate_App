"""Quarantine manager for safely isolating applications before permanent deletion."""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.types import Application


class QuarantineManager:
    def __init__(self, quarantine_dir: str = ".iadcs_quarantine"):
        self.quarantine_path = Path(quarantine_dir).resolve()
        self.quarantine_path.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.quarantine_path / "quarantine_manifest.json"
        self._ensure_manifest()

    def _ensure_manifest(self) -> None:
        if not self.manifest_file.exists():
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump({"items": []}, f, indent=2)

    def _read_manifest(self) -> Dict[str, Any]:
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"items": []}

    def _write_manifest(self, data: Dict[str, Any]) -> None:
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def quarantine_application(self, app: Application) -> Path:
        """Moves an application folder or file into the quarantine directory with timestamped ID."""
        src_path = Path(app.root_path).resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Application path does not exist: {src_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir_name = f"{app.name}_{timestamp}_{app.content_fingerprint[:8]}"
        dest_path = self.quarantine_path / target_dir_name

        # Move folder or file
        shutil.move(str(src_path), str(dest_path))

        # Record in manifest
        manifest_data = self._read_manifest()
        item_entry = {
            "app_name": app.name,
            "original_path": str(src_path),
            "quarantined_path": str(dest_path),
            "fingerprint": app.content_fingerprint,
            "total_size": app.total_size,
            "quarantined_at": datetime.now().isoformat(),
        }
        manifest_data["items"].append(item_entry)
        self._write_manifest(manifest_data)

        return dest_path

    def list_quarantined(self) -> List[Dict[str, Any]]:
        return self._read_manifest().get("items", [])

    def restore_application(self, original_path: str) -> bool:
        """Restores a quarantined application back to its original path."""
        manifest_data = self._read_manifest()
        items = manifest_data.get("items", [])
        target_item = None
        target_idx = -1

        for idx, it in enumerate(items):
            if it.get("original_path") == original_path:
                target_item = it
                target_idx = idx
                break

        if not target_item:
            return False

        q_path = Path(target_item["quarantined_path"])
        orig_p = Path(target_item["original_path"])

        if not q_path.exists():
            return False

        # Ensure parent directory exists
        orig_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(q_path), str(orig_p))

        items.pop(target_idx)
        manifest_data["items"] = items
        self._write_manifest(manifest_data)
        return True
