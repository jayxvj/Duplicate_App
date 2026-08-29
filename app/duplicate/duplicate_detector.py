"""Duplicate grouping, reclaimable space calculation, and verification management."""
from collections import defaultdict
from typing import Dict, List

from app.core.types import Application, AppType, DuplicateGroup, VerificationStatus
from app.duplicate.verifier import verify_applications_byte_by_byte



class DuplicateDetector:
    def __init__(self, auto_verify_bytes: bool = True):
        self.auto_verify_bytes = auto_verify_bytes

    @staticmethod
    def _score_reference_candidate(app: Application) -> int:
        """
        Scores candidates so the best reference copy is at index 0 (Implementation Prompt Sec. 13):
        - Prefers primary program locations (Program Files, Applications, etc.)
        - Demotes backup, download, temp, copy paths
        """
        score = 0
        path_lower = app.root_path.lower()

        # Demote backup/temp/download/archive locations
        for bad_kw in ["backup", "bak", "copy", "temp", "tmp", "download", "downloads", "archive", "old"]:
            if bad_kw in path_lower:
                score -= 10

        # Promote primary program / installed directories
        for good_kw in ["program files", "applications", "usr/bin", "opt", "local/bin", "appdata"]:
            if good_kw in path_lower:
                score += 10

        if app.app_type in (AppType.WINDOWS_INSTALLED, AppType.WINDOWS_PORTABLE):
            score += 5

        return score


    def detect_duplicates(self, applications: List[Application]) -> List[DuplicateGroup]:
        """Groups applications by content fingerprint and identifies duplicate groups."""
        fingerprint_map: Dict[str, List[Application]] = defaultdict(list)

        for app in applications:
            if app.content_fingerprint and app.content_fingerprint not in ["EMPTY_APPLICATION", "NO_READABLE_FILES"]:
                fingerprint_map[app.content_fingerprint].append(app)

        duplicate_groups: List[DuplicateGroup] = []

        for fp, group_apps in fingerprint_map.items():
            if len(group_apps) < 2:
                continue

            # Sort so the best reference / keep candidate is at index 0 (Implementation Prompt Sec. 13)
            group_apps.sort(key=self._score_reference_candidate, reverse=True)

            app_size = group_apps[0].total_size
            app_count = len(group_apps)
            total_size = sum(a.total_size for a in group_apps)
            # Reclaimable size is the size of all duplicates minus 1 original copy
            reclaimable_size = (app_count - 1) * app_size


            status = VerificationStatus.HASH_MATCHED.value
            if self.auto_verify_bytes:
                # Run byte-level verification against first reference copy
                all_matched = True
                for candidate in group_apps[1:]:
                    if not verify_applications_byte_by_byte(group_apps[0], candidate):
                        all_matched = False
                        break
                if all_matched:
                    status = VerificationStatus.BYTE_VERIFIED.value

            group = DuplicateGroup(
                fingerprint=fp,
                application_count=app_count,
                total_size=total_size,
                reclaimable_size=reclaimable_size,
                verification_status=status,
                applications=group_apps,
            )
            duplicate_groups.append(group)

        # Sort duplicate groups by reclaimable size descending
        duplicate_groups.sort(key=lambda g: g.reclaimable_size, reverse=True)
        return duplicate_groups
