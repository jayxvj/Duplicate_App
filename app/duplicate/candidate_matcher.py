"""Multi-stage duplicate candidate matching pipeline."""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

from app.core.types import Application, FileRecord, ScanProgress
from app.hashing.fingerprint import generate_application_fingerprint
from app.hashing.partial_hash import compute_partial_hash
from app.hashing.sha256 import compute_sha256


class CandidateMatcher:
    def __init__(
        self,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ):
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def process_applications(self, applications: List[Application]) -> List[Application]:
        """Runs the multi-stage hashing and fingerprinting pipeline across all applications."""
        self._is_cancelled = False
        progress = ScanProgress(phase="hashing", apps_found=len(applications))

        # 1. Collect all files across applications for batch/parallel hashing
        all_files: List[FileRecord] = []
        for app in applications:
            all_files.extend([f for f in app.files if f.is_readable])

        total_files = len(all_files)
        processed_files = 0

        # Stage 1 & 2: Partial & Full SHA-256 calculation with thread pool
        def hash_file(file_rec: FileRecord) -> None:
            if self._is_cancelled or not file_rec.is_readable:
                return
            # Partial hash
            file_rec.partial_hash = compute_partial_hash(file_rec.absolute_path) or ""
            # Full SHA-256
            file_rec.sha256 = compute_sha256(file_rec.absolute_path) or ""

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for _ in executor.map(hash_file, all_files):
                if self._is_cancelled:
                    break
                processed_files += 1
                progress.files_scanned = processed_files
                progress.percent = (processed_files / max(1, total_files)) * 80.0
                if processed_files % 25 == 0 and self.progress_callback:
                    self.progress_callback(progress)

        # Stage 3: Compute deterministic application fingerprints
        progress.phase = "fingerprinting"
        for i, app in enumerate(applications):
            if self._is_cancelled:
                break
            app.content_fingerprint = generate_application_fingerprint(app.files)
            progress.percent = 80.0 + ((i + 1) / max(1, len(applications))) * 20.0
            if self.progress_callback:
                self.progress_callback(progress)

        return applications
