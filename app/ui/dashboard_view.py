"""Dashboard view with Obsidian Logic metrics, 1-Click Quick Scan, and storage recovery."""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.database.repository import Repository


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


class DashboardView(QWidget):
    navigateTo = pyqtSignal(str)  # signal to switch tabs ("scan", "duplicates", etc.)
    triggerScan = pyqtSignal(list)  # signal with paths list to scan immediately

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header Title with Live Safe Mode Badge
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Application Deduplication Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        subtitle = QLabel("Intelligent content-based application discovery & deterministic SHA-256 deduplication")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Safe Mode Shield Badge
        safe_badge = QLabel("🛡 Safe Mode: Active (OS Protected)")
        safe_badge.setProperty("class", "badge-emerald")
        header_layout.addWidget(safe_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_layout)

        # Metric Cards Row (4 cards matching Stitch Obsidian Logic)
        cards_grid = QGridLayout()
        cards_grid.setSpacing(16)

        self.card_apps = self._create_card("Total Apps Tracked", "0", "Discovered installations", "#c0c1ff")
        self.card_dups = self._create_card("Duplicate Groups", "0", "Redundant groups found", "#f59e0b")
        self.card_space = self._create_card("Reclaimable Storage", "0 B", "100% Safe to clean", "#10b981")
        self.card_cats = self._create_card("Categories", "0", "Organized domains", "#818cf8")

        cards_grid.addWidget(self.card_apps, 0, 0)
        cards_grid.addWidget(self.card_dups, 0, 1)
        cards_grid.addWidget(self.card_space, 0, 2)
        cards_grid.addWidget(self.card_cats, 0, 3)
        layout.addLayout(cards_grid)

        # 1-Click Quick Scan & Folder Drop Zone Hero Card
        drop_card = QFrame()
        drop_card.setObjectName("DropZone")
        drop_layout = QVBoxLayout(drop_card)
        drop_layout.setSpacing(14)
        drop_layout.setContentsMargins(20, 20, 20, 20)

        drop_top = QHBoxLayout()
        drop_title_box = QVBoxLayout()
        drop_title = QLabel("🚀 1-Click Quick Scan & Folder Scanner")
        drop_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        drop_desc = QLabel("Instantly scan common directories or choose custom drives to identify duplicate software without data risk.")
        drop_desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-top: 2px;")
        drop_title_box.addWidget(drop_title)
        drop_title_box.addWidget(drop_desc)
        drop_top.addLayout(drop_title_box)
        drop_top.addStretch()

        btn_quick_scan = QPushButton("⚡ 1-Click Scan Common Folders")
        btn_quick_scan.setProperty("class", "btn-primary")
        btn_quick_scan.clicked.connect(self._scan_common_folders)
        drop_top.addWidget(btn_quick_scan, alignment=Qt.AlignmentFlag.AlignVCenter)
        drop_layout.addLayout(drop_top)

        # Preset Quick Chips
        preset_layout = QHBoxLayout()
        preset_lbl = QLabel("Quick Presets:")
        preset_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        preset_layout.addWidget(preset_lbl)

        btn_preset_downloads = QPushButton("📥 Downloads")
        btn_preset_downloads.setProperty("class", "btn-secondary")
        btn_preset_downloads.clicked.connect(lambda: self._scan_preset(Path.home() / "Downloads"))

        btn_preset_apps = QPushButton("💻 User Profile")
        btn_preset_apps.setProperty("class", "btn-secondary")
        btn_preset_apps.clicked.connect(lambda: self._scan_preset(Path.home()))

        btn_preset_custom = QPushButton("📂 Custom Locations...")
        btn_preset_custom.setProperty("class", "btn-secondary")
        btn_preset_custom.clicked.connect(lambda: self.navigateTo.emit("scan"))

        btn_review_dups = QPushButton("🔍 Review Duplicates")
        btn_review_dups.setProperty("class", "btn-secondary")
        btn_review_dups.clicked.connect(lambda: self.navigateTo.emit("duplicates"))

        preset_layout.addWidget(btn_preset_downloads)
        preset_layout.addWidget(btn_preset_apps)
        preset_layout.addWidget(btn_preset_custom)
        preset_layout.addStretch()
        preset_layout.addWidget(btn_review_dups)
        drop_layout.addLayout(preset_layout)

        layout.addWidget(drop_card)

        # Bottom section: Category breakdown & Recent Activity
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        # Category Card
        self.cat_frame = QFrame()
        self.cat_frame.setProperty("class", "card")
        cat_inner = QVBoxLayout(self.cat_frame)
        cat_head = QLabel("Top Application Categories")
        cat_head.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 8px;")
        cat_inner.addWidget(cat_head)

        self.cat_list_layout = QVBoxLayout()
        cat_inner.addLayout(self.cat_list_layout)
        cat_inner.addStretch()
        bottom_layout.addWidget(self.cat_frame, stretch=1)

        # System Status & Verification Card
        self.activity_frame = QFrame()
        self.activity_frame.setProperty("class", "card")
        act_inner = QVBoxLayout(self.activity_frame)
        act_head = QLabel("System Status & Safeguards")
        act_head.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 8px;")
        act_inner.addWidget(act_head)

        self.status_label = QLabel("System Ready. Run a scan to discover applications.")
        self.status_label.setStyleSheet("color: #dae2fd; font-size: 13px; line-height: 1.5;")
        self.status_label.setWordWrap(True)
        act_inner.addWidget(self.status_label)
        act_inner.addStretch()
        bottom_layout.addWidget(self.activity_frame, stretch=1)

        layout.addLayout(bottom_layout)
        layout.addStretch()

        self.refresh_metrics()

    def _create_card(self, title: str, value: str, subtitle: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 18, 18, 18)

        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "card-title")

        v_lbl = QLabel(value)
        v_lbl.setObjectName("card_val")
        v_lbl.setProperty("class", "card-value")
        v_lbl.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")

        s_lbl = QLabel(subtitle)
        s_lbl.setProperty("class", "card-subtitle")

        c_layout.addWidget(t_lbl)
        c_layout.addWidget(v_lbl)
        c_layout.addWidget(s_lbl)
        return card

    def _scan_preset(self, path: Path):
        if path.exists():
            self.triggerScan.emit([str(path)])
        else:
            self.navigateTo.emit("scan")

    def _scan_common_folders(self):
        targets = []
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            targets.append(str(downloads))
        sample_apps = Path("sample_apps")
        if sample_apps.exists():
            targets.append(str(sample_apps.resolve()))
        if not targets:
            targets.append(str(Path.home()))
        self.triggerScan.emit(targets)

    def refresh_metrics(self):
        apps = self.repo.get_all_applications()
        groups = self.repo.get_all_duplicate_groups()

        total_reclaimable = sum(g.reclaimable_size for g in groups)
        cats = {a.category for a in apps}

        # Update card values
        val_apps = self.card_apps.findChild(QLabel, "card_val")
        if val_apps:
            val_apps.setText(str(len(apps)))

        val_dups = self.card_dups.findChild(QLabel, "card_val")
        if val_dups:
            val_dups.setText(str(len(groups)))

        val_space = self.card_space.findChild(QLabel, "card_val")
        if val_space:
            val_space.setText(format_bytes(total_reclaimable))

        val_cats = self.card_cats.findChild(QLabel, "card_val")
        if val_cats:
            val_cats.setText(str(len(cats)))

        # Update category distribution
        while self.cat_list_layout.count():
            item = self.cat_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat_counts = {}
        for a in apps:
            cat_counts[a.category] = cat_counts.get(a.category, 0) + 1

        if not cat_counts:
            empty_lbl = QLabel("No application data available yet. Click '1-Click Scan' above to discover applications.")
            empty_lbl.setStyleSheet("color: #64748b; font-style: italic;")
            self.cat_list_layout.addWidget(empty_lbl)
        else:
            for cat_name, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                row = QHBoxLayout()
                lbl_name = QLabel(cat_name)
                lbl_name.setStyleSheet("color: #dae2fd; font-weight: 500;")
                lbl_badge = QLabel(f"{count} apps")
                lbl_badge.setProperty("class", "badge-indigo")
                row.addWidget(lbl_name)
                row.addStretch()
                row.addWidget(lbl_badge)
                w = QWidget()
                w.setLayout(row)
                self.cat_list_layout.addWidget(w)

        # Update system status
        latest = self.repo.get_latest_scan()
        if latest:
            self.status_label.setText(
                f"<b>Last Scan:</b> {latest.get('started_at')}<br>"
                f"<b>Apps Analyzed:</b> {latest.get('total_apps')}<br>"
                f"<b>Duplicates Identified:</b> {latest.get('duplicate_groups')} groups<br>"
                f"<b>Potential Storage Recovery:</b> {format_bytes(latest.get('reclaimable_size', 0))}<br><br>"
                "<span style='color:#10b981;'>✓ SHA-256 Multi-Stage Fingerprint Active</span><br>"
                "<span style='color:#10b981;'>✓ OS Protected Directory Safeguards Active</span>"
            )
        else:
            self.status_label.setText(
                "System is ready.<br><br>"
                "<span style='color:#10b981;'>✓ Content-Based Deduplication Engine Loaded</span><br>"
                "<span style='color:#10b981;'>✓ Protected System Directory Guards Enabled</span><br>"
                "<span style='color:#818cf8;'>→ Click '1-Click Scan' to start discovery</span>"
            )
