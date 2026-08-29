"""Duplicate groups review, side-by-side inspection, and safe removal interface."""
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
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.types import Application, DuplicateGroup
from app.database.repository import Repository
from app.removal.removal_manager import RemovalManager
from app.categorization.rule_engine import RuleEngine



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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Duplicate Applications Review")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Content-matched application groups. Compare installations and safely remove redundant copies.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Top Action Bar
        action_bar = QHBoxLayout()
        btn_smart_select = QPushButton("⚡ Auto-Select All Duplicates (Keep 1 Original)")
        btn_smart_select.setProperty("class", "btn-secondary")
        btn_smart_select.clicked.connect(self._smart_select_duplicates)

        btn_deselect = QPushButton("Deselect All")
        btn_deselect.setProperty("class", "btn-secondary")
        btn_deselect.clicked.connect(self._deselect_all)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_data)

        self.btn_remove = QPushButton("🛡 Safely Remove Selected")
        self.btn_remove.setProperty("class", "btn-danger")
        self.btn_remove.clicked.connect(self._prompt_removal)

        action_bar.addWidget(btn_smart_select)
        action_bar.addWidget(btn_deselect)
        action_bar.addWidget(btn_refresh)
        action_bar.addStretch()
        action_bar.addWidget(self.btn_remove)
        layout.addLayout(action_bar)

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

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #94a3b8; font-weight: 500;")
        layout.addWidget(self.lbl_summary)

        self.refresh_data()

    def refresh_data(self):
        self.groups = self.repo.get_all_duplicate_groups()
        self.app_checkboxes.clear()

        # Clear existing group widgets
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.groups:
            empty_card = QFrame()
            empty_card.setProperty("class", "card")
            e_layout = QVBoxLayout(empty_card)
            lbl = QLabel("No duplicate application groups detected.\nYour application footprint is clean or no scan has been run yet.")
            lbl.setStyleSheet("color: #94a3b8; font-size: 14px; text-align: center;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_layout.addWidget(lbl)
            self.groups_layout.addWidget(empty_card)
            self.lbl_summary.setText("Duplicate Groups: 0")
            return

        total_reclaimable = sum(g.reclaimable_size for g in self.groups)
        self.lbl_summary.setText(f"Found {len(self.groups)} duplicate groups. Total Reclaimable Space: {format_bytes(total_reclaimable)}")

        for idx, grp in enumerate(self.groups, 1):
            grp_card = self._build_group_card(idx, grp)
            self.groups_layout.addWidget(grp_card)

    def _build_group_card(self, group_num: int, group: DuplicateGroup) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Header: Group # and badges
        header = QHBoxLayout()
        title = QLabel(f"Duplicate Group #{group_num}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")

        badge_status = QLabel(f"✓ {group.verification_status.upper()}")
        badge_status.setProperty("class", "badge-emerald")

        badge_space = QLabel(f"Reclaimable: {format_bytes(group.reclaimable_size)}")
        badge_space.setProperty("class", "badge-indigo")

        header.addWidget(title)
        header.addWidget(badge_status)
        header.addWidget(badge_space)
        header.addStretch()

        fp_lbl = QLabel(f"Fingerprint: {group.fingerprint[:16]}...")
        fp_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-family: monospace;")
        header.addWidget(fp_lbl)
        card_layout.addLayout(header)

        # Application list inside this group
        for i, app in enumerate(group.applications):
            app_row = QHBoxLayout()
            cb = QCheckBox()
            self.app_checkboxes[app.id or (group_num * 1000 + i)] = cb
            cb.setProperty("app_obj", app)

            is_orig_badge = QLabel("Original Copy" if i == 0 else "Duplicate Copy")
            is_orig_badge.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;" if i == 0 else "color: #f59e0b; font-size: 11px;")

            app_name = QLabel(app.name)
            app_name.setStyleSheet("font-weight: 600; color: #ffffff;")

            category_name = app.category
            if not category_name or category_name == "Other":
                category_name = RuleEngine.get_descriptive_category(app)

            app_cat = QLabel(f"[{category_name}]")
            app_cat.setStyleSheet("color: #818cf8; font-size: 12px; font-weight: 500;")


            app_size = QLabel(format_bytes(app.total_size))
            app_size.setStyleSheet("color: #cbd5e1; font-size: 12px;")

            app_path = QLabel(app.root_path)
            app_path.setStyleSheet("color: #94a3b8; font-size: 12px;")
            app_path.setToolTip(app.root_path)

            app_row.addWidget(cb)
            app_row.addWidget(is_orig_badge)
            app_row.addWidget(app_name)
            app_row.addWidget(app_cat)
            app_row.addWidget(app_size)
            app_row.addWidget(app_path, stretch=1)
            card_layout.addLayout(app_row)

        return card

    def _smart_select_duplicates(self):
        for grp in self.groups:
            # Leave index 0 (original) unchecked, check all subsequent copies (index 1+)
            for i, app in enumerate(grp.applications):
                cb = self.app_checkboxes.get(app.id)
                if cb:
                    cb.setChecked(i > 0)

    def _deselect_all(self):
        for cb in self.app_checkboxes.values():
            cb.setChecked(False)

    def _prompt_removal(self):
        selected_apps: List[Application] = []
        for cb in self.app_checkboxes.values():
            if cb.isChecked():
                app = cb.property("app_obj")
                if app:
                    selected_apps.append(app)

        if not selected_apps:
            QMessageBox.warning(self, "No Selection", "Please select at least one duplicate application to remove.")
            return

        total_bytes = sum(a.total_size for a in selected_apps)

        # Dialog for action confirmation
        dlg = QDialog(self)
        dlg.setWindowTitle("Confirm Safe Removal")
        dlg.setMinimumWidth(450)
        dlg_layout = QVBoxLayout(dlg)

        lbl_head = QLabel(f"You have selected {len(selected_apps)} duplicate application(s) for removal.")
        lbl_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        dlg_layout.addWidget(lbl_head)

        lbl_space = QLabel(f"Total Storage to Recover: {format_bytes(total_bytes)}")
        lbl_space.setStyleSheet("font-size: 13px; color: #10b981; font-weight: 600; margin-bottom: 12px;")
        dlg_layout.addWidget(lbl_space)

        # Mode Selection
        grp_box = QFrame()
        grp_layout = QVBoxLayout(grp_box)
        rb_quarantine = QRadioButton("Quarantine (Recommended - moves to .iadcs_quarantine with restore capability)")
        rb_quarantine.setChecked(True)
        rb_trash = QRadioButton("Send to System Recycle Bin / Trash")
        rb_permanent = QRadioButton("Permanent Binary Deletion")

        grp_layout.addWidget(rb_quarantine)
        grp_layout.addWidget(rb_trash)
        grp_layout.addWidget(rb_permanent)
        dlg_layout.addWidget(grp_box)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btn_box)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            action = "quarantine"
            if rb_trash.isChecked():
                action = "trash"
            elif rb_permanent.isChecked():
                action = "permanent"

            success_count = 0
            failed_count = 0
            for app in selected_apps:
                res = self.removal_mgr.remove_application(app, action=action)
                if res.status == "success":
                    success_count += 1
                else:
                    failed_count += 1

            QMessageBox.information(
                self,
                "Removal Finished",
                f"Removal complete.\nSuccessfully processed: {success_count}\nFailed: {failed_count}"
            )
            self.refresh_data()
            self.duplicatesModified.emit()
