"""Searchable and filterable application inventory table."""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt

from app.database.repository import Repository


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


class InventoryView(QWidget):
    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.all_apps = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Application Inventory")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Comprehensive catalog of all discovered application candidates and content attributes")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Filter and Search Bar
        filter_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by application name or path...")
        self.search_input.textChanged.connect(self._apply_filters)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        self.cat_filter.currentIndexChanged.connect(self._apply_filters)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_data)

        filter_bar.addWidget(self.search_input, stretch=3)
        filter_bar.addWidget(self.cat_filter, stretch=1)
        filter_bar.addWidget(btn_refresh)
        layout.addLayout(filter_bar)

        # Inventory Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "App Name", "Category", "Platform / Type", "Total Size", "Files", "Content Fingerprint", "Location"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.lbl_count = QLabel("Total Applications: 0")
        self.lbl_count.setStyleSheet("color: #94a3b8; font-weight: 500;")
        layout.addWidget(self.lbl_count)

        self.refresh_data()

    def refresh_data(self):
        self.all_apps = self.repo.get_all_applications()

        # Update category dropdown
        current_cat = self.cat_filter.currentText()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem("All Categories")
        cats = sorted({a.category for a in self.all_apps if a.category})
        for c in cats:
            self.cat_filter.addItem(c)
        idx = self.cat_filter.findText(current_cat)
        if idx >= 0:
            self.cat_filter.setCurrentIndex(idx)
        self.cat_filter.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text().strip().lower()
        selected_cat = self.cat_filter.currentText()

        filtered = []
        for app in self.all_apps:
            if selected_cat != "All Categories" and app.category != selected_cat:
                continue
            if query and (query not in app.name.lower() and query not in app.root_path.lower()):
                continue
            filtered.append(app)

        self.table.setRowCount(len(filtered))
        for row_idx, app in enumerate(filtered):
            item_name = QTableWidgetItem(app.name)
            item_name.setForeground(Qt.GlobalColor.white)

            item_cat = QTableWidgetItem(app.category)
            item_type = QTableWidgetItem(f"{app.platform} ({app.app_type.value if hasattr(app.app_type, 'value') else app.app_type})")
            item_size = QTableWidgetItem(format_bytes(app.total_size))
            item_files = QTableWidgetItem(str(app.file_count))
            item_fp = QTableWidgetItem(app.content_fingerprint[:12] + "..." if app.content_fingerprint else "N/A")
            item_path = QTableWidgetItem(app.root_path)

            self.table.setItem(row_idx, 0, item_name)
            self.table.setItem(row_idx, 1, item_cat)
            self.table.setItem(row_idx, 2, item_type)
            self.table.setItem(row_idx, 3, item_size)
            self.table.setItem(row_idx, 4, item_files)
            self.table.setItem(row_idx, 5, item_fp)
            self.table.setItem(row_idx, 6, item_path)

        self.lbl_count.setText(f"Showing {len(filtered)} of {len(self.all_apps)} applications")
