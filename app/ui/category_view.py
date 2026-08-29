"""Category breakdown and categorized application viewer."""
from typing import Dict, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt

from app.core.types import Application
from app.database.repository import Repository
from app.categorization.category_manager import CategoryManager


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


class CategoryView(QWidget):
    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.cat_mgr = CategoryManager(self.repo)
        self.apps: List[Application] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Application Categories")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Rule-based classification breakdown and application distribution")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Content Split: Category List (Left) + Applications Table (Right)
        split_layout = QHBoxLayout()

        # Left Category List
        cat_frame = QFrame()
        cat_frame.setProperty("class", "card")
        cat_layout = QVBoxLayout(cat_frame)
        cat_head = QLabel("Categories")
        cat_head.setStyleSheet("font-weight: 600; color: #ffffff;")
        cat_layout.addWidget(cat_head)

        self.cat_list = QListWidget()
        self.cat_list.setStyleSheet("background-color: #121317; border: 1px solid #232530; border-radius: 6px;")
        self.cat_list.currentItemChanged.connect(self._on_category_selected)
        cat_layout.addWidget(self.cat_list)
        split_layout.addWidget(cat_frame, stretch=1)

        # Right Applications Table
        table_frame = QFrame()
        table_frame.setProperty("class", "card")
        table_layout = QVBoxLayout(table_frame)

        self.table_head = QLabel("Applications in Category")
        self.table_head.setStyleSheet("font-weight: 600; color: #ffffff;")
        table_layout.addWidget(self.table_head)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Files", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table_layout.addWidget(self.table)

        split_layout.addWidget(table_frame, stretch=2)
        layout.addLayout(split_layout)

        self.refresh_data()

    def refresh_data(self):
        self.apps = self.repo.get_all_applications()
        counts = self.cat_mgr.get_category_counts(self.apps)

        self.cat_list.blockSignals(True)
        self.cat_list.clear()

        item_all = QListWidgetItem(f"All Categories ({len(self.apps)})")
        item_all.setData(Qt.ItemDataRole.UserRole, "ALL")
        self.cat_list.addItem(item_all)

        for cat_name, cnt in counts.items():
            item = QListWidgetItem(f"{cat_name} ({cnt})")
            item.setData(Qt.ItemDataRole.UserRole, cat_name)
            self.cat_list.addItem(item)

        self.cat_list.setCurrentRow(0)
        self.cat_list.blockSignals(False)
        self._show_apps_for_category("ALL")

    def _on_category_selected(self, current: QListWidgetItem, previous: QListWidgetItem = None):
        if not current:
            return
        cat_name = current.data(Qt.ItemDataRole.UserRole)
        self._show_apps_for_category(cat_name)

    def _show_apps_for_category(self, cat_name: str):
        if cat_name == "ALL":
            filtered = self.apps
            self.table_head.setText(f"All Applications ({len(filtered)})")
        else:
            filtered = [a for a in self.apps if a.category == cat_name]
            self.table_head.setText(f"Applications in '{cat_name}' ({len(filtered)})")

        self.table.setRowCount(len(filtered))
        for row_idx, app in enumerate(filtered):
            item_name = QTableWidgetItem(app.name)
            item_name.setForeground(Qt.GlobalColor.white)
            item_size = QTableWidgetItem(format_bytes(app.total_size))
            item_files = QTableWidgetItem(str(app.file_count))
            item_path = QTableWidgetItem(app.root_path)

            self.table.setItem(row_idx, 0, item_name)
            self.table.setItem(row_idx, 1, item_size)
            self.table.setItem(row_idx, 2, item_files)
            self.table.setItem(row_idx, 3, item_path)
