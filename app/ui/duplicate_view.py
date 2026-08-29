"""Duplicate groups review, side-by-side inspection, and safe removal interface with Stitch Obsidian Logic."""
from typing import Dict, List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QCheckBox,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.types import Application, DuplicateGroup
from app.database.repository import Repository
from app.removal.removal_manager import RemovalManager


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


class DuplicateView(QWidget):
    duplicatesModified = pyqtSignal()

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.removal_mgr = RemovalManager(self.repo)
        self.groups: List[DuplicateGroup] = []
        self.app_checkboxes: Dict[int, QCheckBox] = {}
        self.search_filter = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title with Live Safe Mode Badge
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Duplicate Applications Review & Clean")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        subtitle = QLabel("Deterministic SHA-256 matched application groups. Easily compare copies and reclaim storage safely.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        safe_badge = QLabel("🛡 Safe Mode: Active")
        safe_badge.setProperty("class", "badge-emerald")
        header_row.addWidget(safe_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_row)

        # Smart Selection & Filter Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "card")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        toolbar_layout.setSpacing(10)

        btn_smart_select = QPushButton("⚡ Auto-Select (Keep 1 Original)")
        btn_smart_select.setProperty("class", "btn-secondary")
        btn_smart_select.clicked.connect(self._smart_select_duplicates)

        btn_keep_newest = QPushButton("🕒 Keep Newest")
        btn_keep_newest.setProperty("class", "btn-secondary")
        btn_keep_newest.clicked.connect(self._keep_newest)

        btn_keep_oldest = QPushButton("🕰 Keep Oldest")
        btn_keep_oldest.setProperty("class", "btn-secondary")
        btn_keep_oldest.clicked.connect(self._keep_oldest)

        btn_deselect = QPushButton("Deselect All")
        btn_deselect.setProperty("class", "btn-secondary")
        btn_deselect.clicked.connect(self._deselect_all)

        toolbar_layout.addWidget(btn_smart_select)
        toolbar_layout.addWidget(btn_keep_newest)
        toolbar_layout.addWidget(btn_keep_oldest)
        toolbar_layout.addWidget(btn_deselect)
        toolbar_layout.addStretch()

        # Search / Filter Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by application name or category...")
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self.search_input)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(btn_refresh)

        layout.addWidget(toolbar_frame)

        # Scroll Area for Duplicate Groups
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: transparent; border: none;")

        self.scroll_content = QWidget()
        self.groups_layout = QVBoxLayout(self.scroll_content)
        self.groups_layout.setSpacing(16)
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        # Sticky Bottom Action Bar
        bottom_card = QFrame()
        bottom_card.setProperty("class", "card")
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_selected_summary = QLabel("Selected: 0 redundant copies (0 B)")
        self.lbl_selected_summary.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 14px;")

        self.btn_quarantine = QPushButton("🛡 Safe Quarantine (Recommended - 100% Recoverable)")
        self.btn_quarantine.setProperty("class", "btn-primary")
        self.btn_quarantine.clicked.connect(lambda: self._prompt_removal("quarantine"))

        self.btn_trash = QPushButton("🗑 Move to Trash")
        self.btn_trash.setProperty("class", "btn-secondary")
        self.btn_trash.clicked.connect(lambda: self._prompt_removal("trash"))

        self.btn_delete = QPushButton("Permanently Delete")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.clicked.connect(lambda: self._prompt_removal("permanent"))

        bottom_layout.addWidget(self.lbl_selected_summary)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_quarantine)
        bottom_layout.addWidget(self.btn_trash)
        bottom_layout.addWidget(self.btn_delete)

        layout.addWidget(bottom_card)

        self.refresh_data()

    def _on_filter_changed(self, text: str):
        self.search_filter = text.strip().lower()
        self._render_groups()

    def refresh_data(self):
        self.groups = self.repo.get_all_duplicate_groups()
        self._render_groups()
        self._smart_select_duplicates()

    def _render_groups(self):
        # Clear layout
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.app_checkboxes.clear()

        filtered_groups = []
        for g in self.groups:
            if not self.search_filter:
                filtered_groups.append(g)
            else:
                match = any(
                    self.search_filter in a.name.lower() or self.search_filter in a.category.lower() or self.search_filter in a.path.lower()
                    for a in g.applications
                )
                if match:
                    filtered_groups.append(g)

        if not filtered_groups:
            empty_frame = QFrame()
            empty_frame.setProperty("class", "card")
            e_layout = QVBoxLayout(empty_frame)
            e_layout.setContentsMargins(32, 32, 32, 32)
            e_title = QLabel("🎉 No Duplicate Applications Found")
            e_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")
            e_desc = QLabel("All tracked applications are unique, or no duplicate groups match your current filter.")
            e_desc.setStyleSheet("color: #94a3b8; font-size: 13px; margin-top: 4px;")
            e_layout.addWidget(e_title, alignment=Qt.AlignmentFlag.AlignCenter)
            e_layout.addWidget(e_desc, alignment=Qt.AlignmentFlag.AlignCenter)
            self.groups_layout.addWidget(empty_frame)
            self._update_selected_summary()
            return

        for grp in filtered_groups:
            card = self._create_group_card(grp)
            self.groups_layout.addWidget(card)

        self._update_selected_summary()

    def _create_group_card(self, grp: DuplicateGroup) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(18, 16, 18, 16)

        # Card Header
        header = QHBoxLayout()
        primary_app = grp.applications[0] if grp.applications else None
        app_name = primary_app.name if primary_app else "Unknown Application"
        category = primary_app.category if primary_app else "Other"

        lbl_name = QLabel(f"📦 {app_name}")
        lbl_name.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")

        cat_badge = QLabel(category)
        cat_badge.setProperty("class", "badge-indigo")

        verified_badge = QLabel("✓ 100% SHA-256 Match")
        verified_badge.setProperty("class", "badge-emerald")

        size_lbl = QLabel(f"Size: {format_bytes(grp.total_size)} ({len(grp.applications)} copies)")
        size_lbl.setStyleSheet("color: #dae2fd; font-weight: 600; font-family: 'JetBrains Mono', monospace;")

        reclaim_lbl = QLabel(f"Reclaimable: {format_bytes(grp.reclaimable_size)}")
        reclaim_lbl.setStyleSheet("color: #10b981; font-weight: 700; font-family: 'JetBrains Mono', monospace;")

        header.addWidget(lbl_name)
        header.addWidget(cat_badge)
        header.addWidget(verified_badge)
        header.addStretch()
        header.addWidget(size_lbl)
        header.addWidget(reclaim_lbl)
        card_layout.addLayout(header)

        # Sub-list of instances
        for idx, app in enumerate(grp.applications):
            row_frame = QFrame()
            row_frame.setStyleSheet("background-color: #131b2e; border: 1px solid #222a3d; border-radius: 8px; padding: 6px 12px;")
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(8, 6, 8, 6)

            cb = QCheckBox()
            cb.stateChanged.connect(self._update_selected_summary)
            self.app_checkboxes[app.id] = cb

            status_chip = QLabel("ORIGINAL (KEEP)" if idx == 0 else "DUPLICATE (REMOVE)")
            status_chip.setProperty("class", "badge-emerald" if idx == 0 else "badge-amber")

            path_lbl = QLabel(app.path)
            path_lbl.setStyleSheet("color: #dae2fd; font-family: 'JetBrains Mono', monospace; font-size: 12px;")

            meta_lbl = QLabel(f"{format_bytes(app.total_size)} • {app.file_count} files")
            meta_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-family: 'JetBrains Mono', monospace;")

            row.addWidget(cb)
            row.addWidget(status_chip)
            row.addWidget(path_lbl, stretch=1)
            row.addWidget(meta_lbl)
            card_layout.addWidget(row_frame)

        return card

    def _smart_select_duplicates(self):
        for grp in self.groups:
            for idx, app in enumerate(grp.applications):
                cb = self.app_checkboxes.get(app.id)
                if cb:
                    cb.setChecked(idx > 0)
        self._update_selected_summary()

    def _keep_newest(self):
        for grp in self.groups:
            sorted_apps = sorted(grp.applications, key=lambda a: a.last_modified or 0, reverse=True)
            for idx, app in enumerate(sorted_apps):
                cb = self.app_checkboxes.get(app.id)
                if cb:
                    cb.setChecked(idx > 0)
        self._update_selected_summary()

    def _keep_oldest(self):
        for grp in self.groups:
            sorted_apps = sorted(grp.applications, key=lambda a: a.last_modified or 0)
            for idx, app in enumerate(sorted_apps):
                cb = self.app_checkboxes.get(app.id)
                if cb:
                    cb.setChecked(idx > 0)
        self._update_selected_summary()

    def _deselect_all(self):
        for cb in self.app_checkboxes.values():
            cb.setChecked(False)
        self._update_selected_summary()

    def _update_selected_summary(self):
        selected_count = 0
        selected_size = 0
        for grp in self.groups:
            for app in grp.applications:
                cb = self.app_checkboxes.get(app.id)
                if cb and cb.isChecked():
                    selected_count += 1
                    selected_size += app.total_size

        self.lbl_selected_summary.setText(f"Selected: {selected_count} redundant copies ({format_bytes(selected_size)})")
        has_selection = selected_count > 0
        self.btn_quarantine.setEnabled(has_selection)
        self.btn_trash.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _prompt_removal(self, action: str):
        selected_app_ids = [app_id for app_id, cb in self.app_checkboxes.items() if cb.isChecked()]
        if not selected_app_ids:
            QMessageBox.warning(self, "No Selection", "Please select at least one duplicate application copy to clean.")
            return

        action_names = {
            "quarantine": "Safe Quarantine (Recoverable)",
            "trash": "Move to Recycle Bin / Trash",
            "permanent": "Permanently Delete",
        }
        title = action_names.get(action, action)

        confirm = QMessageBox.question(
            self,
            f"Confirm {title}",
            f"Are you sure you want to execute '{title}' on {len(selected_app_ids)} selected duplicate applications?\n\n"
            "• OS Protected Directory Safeguards are Active\n"
            "• Drift Verification will ensure file integrity before removal",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            success_count = 0
            fail_count = 0
            for app_id in selected_app_ids:
                res = self.removal_mgr.remove_application(app_id, action=action, confirm_permanent=(action == "permanent"))
                if res.get("success"):
                    success_count += 1
                else:
                    fail_count += 1

            QMessageBox.information(
                self,
                "Operation Completed",
                f"Action '{title}' processed:\n• Successfully cleaned: {success_count}\n• Failed/Blocked by Safety: {fail_count}",
            )
            self.refresh_data()
            self.duplicatesModified.emit()
