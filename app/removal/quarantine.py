"""Quarantine manager for safely isolating applications before permanent deletion."""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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

    def quarantine_application(self, app_or_path: Any, app_name: str = "") -> Optional[Path]:
        """Moves an application folder or file into the quarantine directory with timestamped ID."""
        if hasattr(app_or_path, "root_path"):
            src_path = Path(app_or_path.root_path).resolve()
            name = getattr(app_or_path, "name", src_path.name)
            fingerprint = getattr(app_or_path, "content_fingerprint", "unknown")
            size = getattr(app_or_path, "total_size", 0)
        elif hasattr(app_or_path, "install_path"):
            src_path = Path(app_or_path.install_path).resolve()
            name = getattr(app_or_path, "name", src_path.name)
            fingerprint = getattr(app_or_path, "sha256_hash", "unknown")
            size = getattr(app_or_path, "total_size", 0)
        else:
            src_path = Path(str(app_or_path)).resolve()
            name = app_name or src_path.name
            fingerprint = "manual"
            size = sum(f.stat().st_size for f in src_path.rglob('*') if f.is_file()) if src_path.is_dir() else (src_path.stat().st_size if src_path.exists() else 0)

        if not src_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir_name = f"{name}_{timestamp}_{fingerprint[:8]}"
        dest_path = self.quarantine_path / target_dir_name

        # Move folder or file
        shutil.move(str(src_path), str(dest_path))

        # Record in manifest
        manifest_data = self._read_manifest()
        item_entry = {
            "app_name": name,
            "original_path": str(src_path),
            "quarantined_path": str(dest_path),
            "fingerprint": fingerprint,
            "total_size": size,
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

        quarantined_path = Path(target_item["quarantined_path"])
        dest_path = Path(target_item["original_path"])

        if not quarantined_path.exists():
            return False

        if dest_path.exists():
            return False

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(quarantined_path), str(dest_path))

        items.pop(target_idx)
        manifest_data["items"] = items
        self._write_manifest(manifest_data)
        return True
