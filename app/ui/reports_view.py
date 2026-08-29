"""Reports viewer, JSON export, and audit log inspector."""
import json
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QTabWidget,
)
from PyQt6.QtCore import Qt

from app.database.repository import Repository
from app.reporting.report_generator import ReportGenerator
from app.categorization.category_manager import CategoryManager


class ReportsView(QWidget):
    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.cat_mgr = CategoryManager(self.repo)
        self.latest_report_data = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Reports & Audit Trail")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Generate machine-readable JSON reports and review cryptographic operation audit logs")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Tabs for JSON Report vs Audit Logs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #232530;
                background-color: #121317;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #16181f;
                color: #94a3b8;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #1f1f2e;
                color: #c0c1ff;
                font-weight: 600;
            }
        """)

        # Tab 1: Machine-readable JSON Report
        tab_json = QWidget()
        t_json_layout = QVBoxLayout(tab_json)

        act_row = QHBoxLayout()
        btn_gen = QPushButton("⚡ Generate / Refresh Report")
        btn_gen.setProperty("class", "btn-secondary")
        btn_gen.clicked.connect(self.generate_report)

        btn_export = QPushButton("💾 Export to JSON File")
        btn_export.setProperty("class", "btn-primary")
        btn_export.clicked.connect(self._export_json)

        act_row.addWidget(btn_gen)
        act_row.addWidget(btn_export)
        act_row.addStretch()
        t_json_layout.addLayout(act_row)

        self.txt_json = QTextEdit()
        self.txt_json.setReadOnly(True)
        self.txt_json.setStyleSheet("background-color: #0d0e12; color: #c0c1ff; font-family: Consolas, monospace; font-size: 12px; border: 1px solid #1f2029;")
        t_json_layout.addWidget(self.txt_json)
        self.tabs.addTab(tab_json, "JSON Report")

        # Tab 2: Audit Logs
        tab_logs = QWidget()
        t_logs_layout = QVBoxLayout(tab_logs)

        btn_refresh_logs = QPushButton("Refresh Logs")
        btn_refresh_logs.setProperty("class", "btn-secondary")
        btn_refresh_logs.clicked.connect(self._refresh_logs)
        t_logs_layout.addWidget(btn_refresh_logs)

        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(6)
        self.table_logs.setHorizontalHeaderLabels(["Timestamp", "Operation", "Path", "Status", "Size", "Error Details"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_logs.horizontalHeader().setStretchLastSection(True)
        self.table_logs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t_logs_layout.addWidget(self.table_logs)
        self.tabs.addTab(tab_logs, "Audit Logs")

        layout.addWidget(self.tabs)

        self.generate_report()
        self._refresh_logs()

    def generate_report(self):
        apps = self.repo.get_all_applications()
        groups = self.repo.get_all_duplicate_groups()
        cat_counts = self.cat_mgr.get_category_counts(apps)
        latest_scan = self.repo.get_latest_scan()

        scan_id = latest_scan["scan_id"] if latest_scan else "LATEST"
        paths = latest_scan["paths_scanned"] if latest_scan else []

        self.latest_report_data = ReportGenerator.generate_full_report(
            scan_id=scan_id,
            scan_paths=paths,
            duration_seconds=0.0,
            applications=apps,
            duplicate_groups=groups,
            category_counts=cat_counts,
        )

        formatted = json.dumps(self.latest_report_data, indent=2)
        self.txt_json.setText(formatted)

    def _export_json(self):
        if not self.latest_report_data:
            self.generate_report()

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Report to JSON", "iadcs_report.json", "JSON Files (*.json)")
        if file_path:
            ReportGenerator.export_to_json(self.latest_report_data, file_path)
            QMessageBox.information(self, "Export Successful", f"Report successfully exported to:\n{file_path}")

    def _refresh_logs(self):
        logs = self.repo.get_audit_logs(limit=100)
        self.table_logs.setRowCount(len(logs))

        for row_idx, log in enumerate(logs):
            self.table_logs.setItem(row_idx, 0, QTableWidgetItem(log.get("timestamp", "")))
            self.table_logs.setItem(row_idx, 1, QTableWidgetItem(log.get("operation", "")))
            self.table_logs.setItem(row_idx, 2, QTableWidgetItem(log.get("path", "")))
            self.table_logs.setItem(row_idx, 3, QTableWidgetItem(log.get("status", "")))
            self.table_logs.setItem(row_idx, 4, QTableWidgetItem(str(log.get("size", 0))))
            self.table_logs.setItem(row_idx, 5, QTableWidgetItem(log.get("error") or ""))
