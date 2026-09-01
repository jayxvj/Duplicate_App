"""Quarantine Vault view for IADCS PyQt6 Desktop UI."""
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.database.repository import Repository
from app.removal.quarantine import QuarantineManager


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


class QuarantineView(QWidget):
    quarantineModified = pyqtSignal()

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.qm = QuarantineManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Safe Quarantine Vault")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        subtitle = QLabel("Safely isolated application copies with complete manifests. One-click restoration back to original filesystem paths.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        btn_refresh = QPushButton("Refresh Vault")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_data)
        header_row.addWidget(btn_refresh)
        layout.addLayout(header_row)

        # Scroll Area for Quarantined Applications
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(12)
        self.scroll.setWidget(self.scroll_content)

        layout.addWidget(self.scroll)
        self.refresh_data()

    def refresh_data(self):
        # Clear existing items
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        items = self.qm.list_quarantined()

        if not items:
            empty_card = QFrame()
            empty_card.setProperty("class", "card")
            empty_layout = QVBoxLayout(empty_card)
            empty_layout.setContentsMargins(32, 48, 32, 48)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_empty = QLabel("Quarantine Vault is Empty")
            lbl_empty.setStyleSheet("font-size: 18px; font-weight: 700; color: #10b981;")
            lbl_sub = QLabel("No application copies are currently quarantined. Use the Duplicate Review screen to safely isolate redundant files.")
            lbl_sub.setStyleSheet("color: #94a3b8; font-size: 13px; margin-top: 4px;")
            empty_layout.addWidget(lbl_empty, alignment=Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(lbl_sub, alignment=Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(empty_card)
            self.scroll_layout.addStretch()
            return

        for item_data in items:
            card = self._create_quarantine_card(item_data)
            self.scroll_layout.addWidget(card)

        self.scroll_layout.addStretch()

    def _create_quarantine_card(self, item_data: Dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)

        # Left Info
        info_layout = QVBoxLayout()
        name_row = QHBoxLayout()
        lbl_name = QLabel(item_data.get("app_name", "Unknown Application"))
        lbl_name.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        badge = QLabel("QUARANTINED")
        badge.setProperty("class", "badge-emerald")
        name_row.addWidget(lbl_name)
        name_row.addWidget(badge)
        name_row.addStretch()
        info_layout.addLayout(name_row)

        orig_path = item_data.get("original_path", "")
        lbl_path = QLabel(f"Original: {orig_path}")
        lbl_path.setStyleSheet("color: #94a3b8; font-size: 12px; font-family: monospace;")
        info_layout.addWidget(lbl_path)

        size_bytes = item_data.get("total_size", 0)
        date_str = item_data.get("quarantined_at", "Recent")
        lbl_meta = QLabel(f"Size: {format_bytes(size_bytes)}  |  Date: {date_str}")
        lbl_meta.setStyleSheet("color: #64748b; font-size: 12px;")
        info_layout.addWidget(lbl_meta)

        card_layout.addLayout(info_layout, stretch=1)

        # Right Restore Button
        btn_restore = QPushButton("↺  Restore Application")
        btn_restore.setProperty("class", "btn-primary")
        btn_restore.setStyleSheet("background-color: #4f46e5; color: white; padding: 8px 16px; border-radius: 6px; font-weight: 600;")
        btn_restore.clicked.connect(lambda _, p=orig_path: self._restore_item(p))
        card_layout.addWidget(btn_restore, alignment=Qt.AlignmentFlag.AlignVCenter)

        return card

    def _restore_item(self, original_path: str):
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Are you sure you want to restore this application back to:\n\n{original_path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.qm.restore_application(original_path)
            if success:
                QMessageBox.information(self, "Success", "Application has been restored successfully!")
                self.refresh_data()
                self.quarantineModified.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to restore application. The destination path may already exist.")
