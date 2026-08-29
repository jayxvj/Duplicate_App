"""Configurable rule editor and categorization manager view."""
from typing import List

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QMessageBox,
    QDialog,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.types import CategoryRule
from app.database.repository import Repository
from app.categorization.category_manager import CategoryManager


class RuleDialog(QDialog):
    def __init__(self, rule: CategoryRule = None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("Edit Rule" if rule else "Add Categorization Rule")
        self.setMinimumWidth(380)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Category
        layout.addWidget(QLabel("Category Name:"))
        self.cat_input = QLineEdit()
        self.cat_input.setPlaceholderText("e.g. Development, Media, Security")
        if self.rule:
            self.cat_input.setText(self.rule.category)
        layout.addWidget(self.cat_input)

        # Field
        layout.addWidget(QLabel("Field to Match:"))
        self.field_combo = QComboBox()
        self.field_combo.addItems(["path", "name", "executable", "app_type", "size"])
        if self.rule:
            self.field_combo.setCurrentText(self.rule.field)
        layout.addWidget(self.field_combo)

        # Operator
        layout.addWidget(QLabel("Operator:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(["contains", "equals", "starts_with", "ends_with", "regex", "gt", "lt"])
        if self.rule:
            self.op_combo.setCurrentText(self.rule.operator)
        layout.addWidget(self.op_combo)

        # Value
        layout.addWidget(QLabel("Match Value:"))
        self.val_input = QLineEdit()
        self.val_input.setPlaceholderText("e.g. code, vlc, .exe")
        if self.rule:
            self.val_input.setText(self.rule.value)
        layout.addWidget(self.val_input)

        # Priority
        layout.addWidget(QLabel("Priority (Higher evaluated first):"))
        self.prio_spin = QSpinBox()
        self.prio_spin.setRange(1, 1000)
        self.prio_spin.setValue(self.rule.priority if self.rule else 50)
        layout.addWidget(self.prio_spin)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self):
        if not self.cat_input.text().strip() or not self.val_input.text().strip():
            QMessageBox.warning(self, "Invalid Input", "Please provide both Category and Match Value.")
            return
        self.accept()

    def get_rule_data(self) -> CategoryRule:
        return CategoryRule(
            id=self.rule.id if self.rule else None,
            category=self.cat_input.text().strip(),
            field=self.field_combo.currentText(),
            operator=self.op_combo.currentText(),
            value=self.val_input.text().strip(),
            priority=self.prio_spin.value(),
            enabled=True,
        )


class RulesView(QWidget):
    rulesModified = pyqtSignal()

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.cat_mgr = CategoryManager(self.repo)
        self.rules: List[CategoryRule] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Categorization Rules")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        subtitle = QLabel("Configure rule priorities, condition operators, and match patterns for automated categorization")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Action Bar
        action_bar = QHBoxLayout()
        btn_add = QPushButton("+ Add New Rule")
        btn_add.setProperty("class", "btn-primary")
        btn_add.clicked.connect(self._add_rule)

        btn_delete = QPushButton("Delete Selected")
        btn_delete.setProperty("class", "btn-secondary")
        btn_delete.clicked.connect(self._delete_selected_rule)

        btn_recat = QPushButton("⚡ Re-categorize All Applications")
        btn_recat.setProperty("class", "btn-secondary")
        btn_recat.clicked.connect(self._recategorize_all)

        action_bar.addWidget(btn_add)
        action_bar.addWidget(btn_delete)
        action_bar.addWidget(btn_recat)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        # Rules Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Category", "Field", "Operator", "Match Value", "Priority"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        self.rules = self.cat_mgr.get_rules()
        self.table.setRowCount(len(self.rules))

        for row_idx, rule in enumerate(self.rules):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(rule.id)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(rule.category))
            self.table.setItem(row_idx, 2, QTableWidgetItem(rule.field))
            self.table.setItem(row_idx, 3, QTableWidgetItem(rule.operator))
            self.table.setItem(row_idx, 4, QTableWidgetItem(rule.value))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(rule.priority)))

    def _add_rule(self):
        dlg = RuleDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_rule = dlg.get_rule_data()
            self.repo.save_rule(new_rule)
            self.refresh_data()
            self.rulesModified.emit()

    def _delete_selected_rule(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a rule to delete.")
            return

        rule_id_item = self.table.item(row, 0)
        if rule_id_item:
            rule_id = int(rule_id_item.text())
            self.repo.delete_rule(rule_id)
            self.refresh_data()
            self.rulesModified.emit()

    def _recategorize_all(self):
        apps = self.repo.get_all_applications()
        if not apps:
            QMessageBox.information(self, "No Apps", "No applications in database to categorize.")
            return

        self.cat_mgr.categorize_applications(apps)
        for app in apps:
            self.repo.save_application(app)

        QMessageBox.information(self, "Categorization Complete", f"Successfully re-categorized {len(apps)} applications.")
        self.rulesModified.emit()
