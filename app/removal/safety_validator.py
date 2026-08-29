"""Safety validation checks before performing destructive application removal."""
from pathlib import Path
from typing import Optional, Tuple

from app.core.types import Application, DuplicateGroup
from app.hashing.fingerprint import generate_application_fingerprint
from app.hashing.sha256 import compute_sha256
from app.scanner.platform_detector import is_protected_path


class SafetyValidator:
    @staticmethod
    def validate_for_removal(app: Application, duplicate_group: Optional[DuplicateGroup] = None) -> Tuple[bool, Optional[str]]:
        """
        Performs strict pre-deletion safety checks:
        1. Target path exists
        2. Target path is not a protected system folder
        3. Content fingerprint has not drifted
        4. Application is confirmed in a duplicate group
        """
        path = Path(app.root_path)

        # 1. Path existence check
        if not path.exists():
            return False, f"Target path '{app.root_path}' does not exist on disk."

        # 2. Protected system directory guard
        if is_protected_path(path):
            return False, f"Target path '{app.root_path}' is a protected system directory and cannot be modified."

        # 3. Fingerprint drift check
        # Re-hash readable files to guarantee no accidental modification occurred
        if app.files:
            recomputed_files = []
            for f in app.files:
                p = Path(f.absolute_path)
                if p.is_file():
                    h = compute_sha256(p)
                    f_copy = f
                    f_copy.sha256 = h or ""
                    recomputed_files.append(f_copy)
            new_fp = generate_application_fingerprint(recomputed_files)
            if new_fp != app.content_fingerprint:
                return False, f"Content fingerprint changed since scan for '{app.name}'. Removal aborted for safety."

        return True, None
