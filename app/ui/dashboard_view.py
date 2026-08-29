"""Dashboard view with metrics, storage recovery hero card, and quick insights."""
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

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("System Overview")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Intelligent content-based application discovery & deduplication analytics")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Metric Cards Row (4 cards)
        cards_grid = QGridLayout()
        cards_grid.setSpacing(16)

        self.card_apps = self._create_card("Total Discovered Apps", "0", "Discovered", "#6366f1")
        self.card_dups = self._create_card("Duplicate Groups", "0", "Active Groups", "#f59e0b")
        self.card_space = self._create_card("Reclaimable Storage", "0 B", "Potential Recovery", "#10b981")
        self.card_cats = self._create_card("Categories", "0", "Organized", "#8b5cf6")

        cards_grid.addWidget(self.card_apps, 0, 0)
        cards_grid.addWidget(self.card_dups, 0, 1)
        cards_grid.addWidget(self.card_space, 0, 2)
        cards_grid.addWidget(self.card_cats, 0, 3)
        layout.addLayout(cards_grid)

        # Hero Storage Recovery Banner
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_card.setStyleSheet("""
            QFrame#HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1b2e, stop:1 #13141f);
                border: 1px solid #2d2f45;
                border-radius: 10px;
                padding: 24px;
            }
        """)
        hero_layout = QHBoxLayout(hero_card)

        hero_text_layout = QVBoxLayout()
        hero_title = QLabel("Optimize Local Application Footprint")
        hero_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #ffffff;")
        hero_desc = QLabel("Scan drives to discover redundant installations and recover storage through deterministic SHA-256 fingerprinting.")
        hero_desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-top: 4px;")
        hero_text_layout.addWidget(hero_title)
        hero_text_layout.addWidget(hero_desc)

        hero_actions = QHBoxLayout()
        btn_scan = QPushButton("Start New Scan")
        btn_scan.setProperty("class", "btn-primary")
        btn_scan.clicked.connect(lambda: self.navigateTo.emit("scan"))

        btn_review = QPushButton("Review Duplicates")
        btn_review.setProperty("class", "btn-secondary")
        btn_review.clicked.connect(lambda: self.navigateTo.emit("duplicates"))

        hero_actions.addWidget(btn_scan)
        hero_actions.addWidget(btn_review)

        hero_layout.addLayout(hero_text_layout, stretch=3)
        hero_layout.addLayout(hero_actions, stretch=1)
        layout.addWidget(hero_card)

        # Bottom section: Category breakdown & Recent Activity
        bottom_layout = QHBoxLayout()

        # Category Card
        self.cat_frame = QFrame()
        self.cat_frame.setProperty("class", "card")
        cat_inner = QVBoxLayout(self.cat_frame)
        cat_head = QLabel("Category Distribution")
        cat_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 8px;")
        cat_inner.addWidget(cat_head)

        self.cat_list_layout = QVBoxLayout()
        cat_inner.addLayout(self.cat_list_layout)
        cat_inner.addStretch()
        bottom_layout.addWidget(self.cat_frame, stretch=1)

        # Recent Activity Card
        self.activity_frame = QFrame()
        self.activity_frame.setProperty("class", "card")
        act_inner = QVBoxLayout(self.activity_frame)
        act_head = QLabel("System Status & Verification")
        act_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 8px;")
        act_inner.addWidget(act_head)

        self.status_label = QLabel("System Ready. Run a scan to discover applications.")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.5;")
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
        c_layout.setContentsMargins(16, 16, 16, 16)

        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "card-title")

        v_lbl = QLabel(value)
        v_lbl.setObjectName("card_val")
        v_lbl.setProperty("class", "card-value")
        v_lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")

        s_lbl = QLabel(subtitle)
        s_lbl.setProperty("class", "card-subtitle")

        c_layout.addWidget(t_lbl)
        c_layout.addWidget(v_lbl)
        c_layout.addWidget(s_lbl)
        return card

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
        # Clear layout
        while self.cat_list_layout.count():
            item = self.cat_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat_counts = {}
        for a in apps:
            cat_counts[a.category] = cat_counts.get(a.category, 0) + 1

        if not cat_counts:
            empty_lbl = QLabel("No application data available yet.")
            empty_lbl.setStyleSheet("color: #64748b; font-style: italic;")
            self.cat_list_layout.addWidget(empty_lbl)
        else:
            for cat_name, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                row = QHBoxLayout()
                lbl_name = QLabel(cat_name)
                lbl_name.setStyleSheet("color: #e3e2e7; font-weight: 500;")
                lbl_badge = QLabel(f"{count} apps")
                lbl_badge.setStyleSheet("color: #818cf8; font-weight: 600;")
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
                f"Last Scan: {latest.get('started_at')}\n"
                f"Applications Processed: {latest.get('total_apps')}\n"
                f"Duplicates Identified: {latest.get('duplicate_groups')}\n"
                f"Reclaimable Storage: {format_bytes(latest.get('reclaimable_size', 0))}\n\n"
                "✓ SHA-256 Multi-Stage Pipeline Active\n"
                "✓ Safety Validator & Protected Directory Guards Enabled"
            )
        else:
            self.status_label.setText("No recent scans recorded. Ready to configure and run initial scan.")
