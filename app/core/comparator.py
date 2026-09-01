"""
Duplicate comparator — groups applications by identical app_signature.

v1: exact matches only.
Two AppRecords are duplicates iff app_signature A == app_signature B
and both signatures are non-None.

No auto-selection of reference app — that is left entirely to the user.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import List

from app.data.models import AppRecord, DuplicateGroup

logger = logging.getLogger(__name__)


class Comparator:
    """Groups apps with identical content signatures into DuplicateGroups."""

    def find_duplicates(
        self,
        apps: List[AppRecord],
        scan_id: int | None = None,
    ) -> List[DuplicateGroup]:
        """
        Return a list of DuplicateGroup objects, one per set of apps
        sharing the same non-None app_signature.

        Groups with only one member are not duplicates and are excluded.
        """
        # Index by signature
        sig_map: dict[str, List[AppRecord]] = defaultdict(list)
        for app in apps:
            if app.app_signature:
                sig_map[app.app_signature].append(app)

        groups: List[DuplicateGroup] = []
        for sig, members in sig_map.items():
            if len(members) < 2:
                continue   # unique app — not a duplicate

            group = DuplicateGroup(
                group_signature=sig,
                match_type="exact",
                similarity=1.0,
                reference_app_id=None,   # user will designate
                scan_id=scan_id,
                members=list(members),
            )
            groups.append(group)
            logger.info(
                "Duplicate group found: signature=%s... members=%d paths=%s",
                sig[:16],
                len(members),
                [m.install_path for m in members],
            )

        logger.info(
            "Comparator: %d apps → %d duplicate groups",
            len(apps), len(groups),
        )
        return groups
