"""Main application window and navigation controller with Stitch Obsidian Logic styling."""
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
)
from PyQt6.QtCore import Qt

from app.database.db import init_db
from app.database.repository import Repository
from app.ui.styles import MAIN_STYLE
from app.ui.dashboard_view import DashboardView
from app.ui.scan_view import ScanView
from app.ui.inventory_view import InventoryView
from app.ui.duplicate_view import DuplicateView
from app.ui.category_view import CategoryView
from app.ui.rules_view import RulesView
from app.ui.quarantine_view import QuarantineView
from app.ui.reports_view import ReportsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IADCS Sentinel — Intelligent Application Deduplication System")
        self.resize(1240, 800)
        self.setMinimumSize(1000, 680)

        # Initialize SQLite Database & Repository
        init_db()
        self.repo = Repository()

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 20)
        side_layout.setSpacing(6)

        # App Logo & Branding
        lbl_title = QLabel("IADCS Sentinel")
        lbl_title.setObjectName("SidebarTitle")
        lbl_sub = QLabel("INTELLIGENT DEDUPLICATION")
        lbl_sub.setObjectName("SidebarSubtitle")
        side_layout.addWidget(lbl_title)
        side_layout.addWidget(lbl_sub)

        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.setExclusive(True)

        self.btn_nav_dash = self._create_nav_button("📊  Dashboard", 0)
        self.btn_nav_scan = self._create_nav_button("🔍  Scan Directories", 1)
        self.btn_nav_dup = self._create_nav_button("📋  Duplicates Review", 2)
        self.btn_nav_inv = self._create_nav_button("📦  Inventory", 3)
        self.btn_nav_cat = self._create_nav_button("🏷️  Categories", 4)
        self.btn_nav_rules = self._create_nav_button("⚙️  Rule Engine", 5)
        self.btn_nav_quar = self._create_nav_button("🛡️  Quarantine Vault", 6)
        self.btn_nav_rep = self._create_nav_button("📄  Reports & Audit", 7)

        for btn in [
            self.btn_nav_dash,
            self.btn_nav_scan,
            self.btn_nav_dup,
            self.btn_nav_inv,
            self.btn_nav_cat,
            self.btn_nav_rules,
            self.btn_nav_quar,
            self.btn_nav_rep,
        ]:
            side_layout.addWidget(btn)

        side_layout.addStretch()

        # Footer info in sidebar
        lbl_safe = QLabel("🛡️ Safe Mode: Active")
        lbl_safe.setProperty("class", "badge-emerald")
        lbl_safe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(lbl_safe)

        lbl_ver = QLabel("v1.2.0 • Obsidian Logic Native")
        lbl_ver.setStyleSheet("color: #475569; font-size: 11px; padding: 6px 12px; text-align: center;")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(lbl_ver)

        root_layout.addWidget(sidebar)

        # 2. Main Stacked Content Views
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView(self.repo)
        self.view_scan = ScanView(self.repo)
        self.view_duplicate = DuplicateView(self.repo)
        self.view_inventory = InventoryView(self.repo)
        self.view_category = CategoryView(self.repo)
        self.view_rules = RulesView(self.repo)
        self.view_quarantine = QuarantineView(self.repo)
        self.view_reports = ReportsView(self.repo)

        self.stack.addWidget(self.view_dashboard)   # Index 0
        self.stack.addWidget(self.view_scan)        # Index 1
        self.stack.addWidget(self.view_duplicate)   # Index 2
        self.stack.addWidget(self.view_inventory)   # Index 3
        self.stack.addWidget(self.view_category)    # Index 4
        self.stack.addWidget(self.view_rules)       # Index 5
        self.stack.addWidget(self.view_quarantine)  # Index 6
        self.stack.addWidget(self.view_reports)     # Index 7

        root_layout.addWidget(self.stack, stretch=1)

        # Connect Signals
        self.btn_nav_dash.setChecked(True)
        self.view_dashboard.navigateTo.connect(self._navigate_by_name)
        self.view_dashboard.triggerScan.connect(self._on_trigger_scan)
        self.view_scan.navigateToReview.connect(lambda: self._navigate_by_name("duplicates"))
        self.view_scan.scanCompleted.connect(self._on_data_updated)
        self.view_duplicate.duplicatesModified.connect(self._on_data_updated)
        self.view_quarantine.quarantineModified.connect(self._on_data_updated)
        self.view_rules.rulesModified.connect(self._on_data_updated)

    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        self.nav_btn_group.addButton(btn, index)
        btn.clicked.connect(lambda: self.switch_view(index))
        return btn

    def switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, "refresh_data"):
            current_widget.refresh_data()
        elif hasattr(current_widget, "refresh_metrics"):
            current_widget.refresh_metrics()

    def _navigate_by_name(self, name: str):
        mapping = {
            "dashboard": 0,
            "scan": 1,
            "duplicates": 2,
            "inventory": 3,
            "categories": 4,
            "rules": 5,
            "quarantine": 6,
            "reports": 7,
        }
        idx = mapping.get(name, 0)
        btn = self.nav_btn_group.button(idx)
        if btn:
            btn.setChecked(True)
        self.switch_view(idx)

    def _on_trigger_scan(self, paths: list):
        self._navigate_by_name("scan")
        self.view_scan.start_scan_with_paths(paths)

    def _on_data_updated(self):
        # Refresh all views with updated data
        self.view_dashboard.refresh_metrics()
        self.view_inventory.refresh_data()
        self.view_duplicate.refresh_data()
        self.view_category.refresh_data()
        self.view_quarantine.refresh_data()
        self.view_reports.generate_report()


def launch_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(MAIN_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    launch_gui()
