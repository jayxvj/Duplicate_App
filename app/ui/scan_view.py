"""Scan configuration and live execution view with background threading."""
import time
import uuid
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QListWidget,
    QLineEdit,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from app.core.types import Application, DuplicateGroup, ScanProgress
from app.database.repository import Repository
from app.scanner.directory_scanner import DirectoryScanner
from app.duplicate.candidate_matcher import CandidateMatcher
from app.duplicate.duplicate_detector import DuplicateDetector
from app.categorization.category_manager import CategoryManager
from app.logging.audit_logger import AuditLogger


class ScanWorker(QThread):
    progress_update = pyqtSignal(ScanProgress)
    scan_complete = pyqtSignal(str, list, list, float)  # scan_id, apps, groups, duration
    scan_error = pyqtSignal(str)

    def __init__(self, paths: List[str], exclusions: List[str], repository: Repository):
        super().__init__()
        self.paths = paths
        self.exclusions = exclusions
        self.repo = repository
        self.scanner: Optional[DirectoryScanner] = None
        self.matcher: Optional[CandidateMatcher] = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self.scanner:
            self.scanner.cancel()
        if self.matcher:
            self.matcher.cancel()

    def run(self):
        try:
            scan_id = str(uuid.uuid4())[:8]
            start_time = time.time()

            self.scanner = DirectoryScanner(
                exclusions=self.exclusions,
                progress_callback=lambda p: self.progress_update.emit(p),
            )
            apps = self.scanner.scan_directories([Path(p) for p in self.paths])

            if self._is_cancelled:
                return

            self.matcher = CandidateMatcher(
                progress_callback=lambda p: self.progress_update.emit(p)
            )
            apps = self.matcher.process_applications(apps)

            if self._is_cancelled:
                return

            cat_mgr = CategoryManager(self.repo)
            apps = cat_mgr.categorize_applications(apps)

            # Persist apps
            for app in apps:
                app.scan_id = scan_id
                self.repo.save_application(app)

            # Group duplicates
            detector = DuplicateDetector(auto_verify_bytes=True)
            groups = detector.detect_duplicates(apps)

            self.repo.clear_duplicate_groups()
            for grp in groups:
                self.repo.save_duplicate_group(grp)

            duration = time.time() - start_time
            total_size = sum(a.total_size for a in apps)
            reclaimable = sum(g.reclaimable_size for g in groups)

            self.repo.record_scan(
                scan_id=scan_id,
                started_at=time.ctime(start_time),
                completed_at=time.ctime(),
                total_apps=len(apps),
                duplicate_groups=len(groups),
                total_size=total_size,
                reclaimable_size=reclaimable,
                paths_scanned=self.paths,
            )

            AuditLogger().log(
                "scan_completed",
                details={
                    "scan_id": scan_id,
                    "apps": len(apps),
                    "duplicate_groups": len(groups),
                    "reclaimable": reclaimable,
                },
            )

            self.scan_complete.emit(scan_id, apps, groups, duration)

        except Exception as e:
            self.scan_error.emit(str(e))


class ScanView(QWidget):
    scanCompleted = pyqtSignal()

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.worker: Optional[ScanWorker] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Title
        title_box = QVBoxLayout()
        title = QLabel("Scan Manager")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Configure scan directories, exclusions, and initiate content analysis")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Main Configuration Layout
        config_layout = QHBoxLayout()

        # Left: Target Directories
        dir_frame = QFrame()
        dir_frame.setProperty("class", "card")
        dir_layout = QVBoxLayout(dir_frame)
        dir_head = QLabel("Target Directories to Scan")
        dir_head.setStyleSheet("font-weight: 600; color: #ffffff;")
        dir_layout.addWidget(dir_head)

        self.dir_list = QListWidget()
        self.dir_list.setStyleSheet("background-color: #121317; border: 1px solid #232530; border-radius: 6px;")
        dir_layout.addWidget(self.dir_list)

        dir_btn_row = QHBoxLayout()
        btn_add_dir = QPushButton("+ Add Directory")
        btn_add_dir.setProperty("class", "btn-secondary")
        btn_add_dir.clicked.connect(self._add_directory)

        btn_rem_dir = QPushButton("Remove")
        btn_rem_dir.setProperty("class", "btn-secondary")
        btn_rem_dir.clicked.connect(self._remove_directory)

        dir_btn_row.addWidget(btn_add_dir)
        dir_btn_row.addWidget(btn_rem_dir)
        dir_layout.addLayout(dir_btn_row)
        config_layout.addWidget(dir_frame, stretch=1)

        # Right: Exclusions & Filters
        excl_frame = QFrame()
        excl_frame.setProperty("class", "card")
        excl_layout = QVBoxLayout(excl_frame)
        excl_head = QLabel("Exclusion Filters")
        excl_head.setStyleSheet("font-weight: 600; color: #ffffff;")
        excl_layout.addWidget(excl_head)

        self.excl_list = QListWidget()
        self.excl_list.setStyleSheet("background-color: #121317; border: 1px solid #232530; border-radius: 6px;")
        # Add default exclusions
        for default_ex in ["$RECYCLE.BIN", "System Volume Information", "node_modules", ".git", ".venv", "__pycache__", ".iadcs_quarantine"]:
            self.excl_list.addItem(default_ex)
        excl_layout.addWidget(self.excl_list)

        excl_input_row = QHBoxLayout()
        self.excl_input = QLineEdit()
        self.excl_input.setPlaceholderText("e.g. temp, downloads")
        btn_add_excl = QPushButton("+ Add Exclusion")
        btn_add_excl.setProperty("class", "btn-secondary")
        btn_add_excl.clicked.connect(self._add_exclusion)
        excl_input_row.addWidget(self.excl_input)
        excl_input_row.addWidget(btn_add_excl)
        excl_layout.addLayout(excl_input_row)

        config_layout.addWidget(excl_frame, stretch=1)
        layout.addLayout(config_layout)

        # Scan Action & Live Progress Card
        prog_frame = QFrame()
        prog_frame.setProperty("class", "card")
        prog_layout = QVBoxLayout(prog_frame)

        act_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start Content-Based Scan")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setStyleSheet("padding: 10px 24px; font-size: 14px;")
        self.btn_start.clicked.connect(self.start_scan)

        self.btn_cancel = QPushButton("⏹ Cancel Scan")
        self.btn_cancel.setProperty("class", "btn-danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_scan)

        act_row.addWidget(self.btn_start)
        act_row.addWidget(self.btn_cancel)
        act_row.addStretch()
        prog_layout.addLayout(act_row)

        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-weight: 500; margin-top: 10px;")
        prog_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)

        self.lbl_current_file = QLabel("")
        self.lbl_current_file.setStyleSheet("color: #64748b; font-size: 11px;")
        prog_layout.addWidget(self.lbl_current_file)

        layout.addWidget(prog_frame)
        layout.addStretch()

    def _add_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            # Avoid duplicates
            items = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
            if path not in items:
                self.dir_list.addItem(path)

    def _remove_directory(self):
        row = self.dir_list.currentRow()
        if row >= 0:
            self.dir_list.takeItem(row)

    def _add_exclusion(self):
        text = self.excl_input.text().strip()
        if text:
            self.excl_list.addItem(text)
            self.excl_input.clear()

    def start_scan(self):
        paths = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
        if not paths:
            QMessageBox.warning(self, "No Scan Target", "Please add at least one directory to scan.")
            return

        exclusions = [self.excl_list.item(i).text() for i in range(self.excl_list.count())]

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Status: Initializing scan...")

        self.worker = ScanWorker(paths, exclusions, self.repo)
        self.worker.progress_update.connect(self._on_progress)
        self.worker.scan_complete.connect(self._on_complete)
        self.worker.scan_error.connect(self._on_error)
        self.worker.start()

    def cancel_scan(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("Status: Scan cancelled by user.")
            self.btn_start.setEnabled(True)
            self.btn_cancel.setEnabled(False)

    def _on_progress(self, p: ScanProgress):
        self.progress_bar.setValue(int(p.percent))
        phase_str = p.phase.capitalize()
        self.lbl_status.setText(f"Status: {phase_str} — Discovered {p.apps_found} apps, {p.files_scanned} files processed")
        if p.current_path:
            self.lbl_current_file.setText(f"Current: {p.current_path}")

    def _on_complete(self, scan_id: str, apps: list, groups: list, duration: float):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"Status: Completed! Found {len(apps)} apps and {len(groups)} duplicate groups in {duration:.2f}s.")
        self.lbl_current_file.setText("")
        QMessageBox.information(self, "Scan Complete", f"Scan finished successfully in {duration:.2f}s.\nDiscovered {len(apps)} applications.\nDetected {len(groups)} duplicate groups.")
        self.scanCompleted.emit()

    def _on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(f"Status: Error occurred — {err_msg}")
        QMessageBox.critical(self, "Scan Error", f"An error occurred during scan:\n{err_msg}")
