"""Obsidian Logic dark glassmorphism styling for IADCS PyQt6 Desktop UI (Generated via Stitch Design System)."""

MAIN_STYLE = """
/* Global Application Base (Obsidian #0b1326) */
QWidget {
    background-color: #0b1326;
    color: #dae2fd;
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

/* Sidebar Navigation (#131b2e) */
QFrame#Sidebar {
    background-color: #131b2e;
    border-right: 1px solid #222a3d;
    min-width: 230px;
    max-width: 250px;
}

QLabel#SidebarTitle {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    padding: 20px 16px 4px 16px;
    letter-spacing: -0.02em;
}

QLabel#SidebarSubtitle {
    color: #818cf8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    padding: 0px 16px 20px 16px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 11px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    margin: 3px 10px;
}

QPushButton.nav-btn:hover {
    background-color: rgba(99, 102, 241, 0.08);
    color: #ffffff;
}

QPushButton.nav-btn:checked {
    background-color: #1e293b;
    color: #c0c1ff;
    font-weight: 600;
    border-left: 3px solid #6366f1;
}

/* Header & Cards (#171f33) */
QFrame.card {
    background-color: #171f33;
    border: 1px solid #222a3d;
    border-radius: 12px;
    padding: 18px;
}

QFrame.card:hover {
    border-color: #2d3449;
}

QLabel.card-title {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

QLabel.card-value {
    color: #ffffff;
    font-size: 26px;
    font-weight: 700;
    margin-top: 6px;
}

QLabel.card-subtitle {
    color: #10b981;
    font-size: 12px;
    font-weight: 500;
    margin-top: 3px;
}

/* Drag-and-Drop & Quick Action Zone */
QFrame#DropZone {
    background-color: rgba(23, 31, 51, 0.6);
    border: 2px dashed #4f46e5;
    border-radius: 14px;
    padding: 24px;
}

QFrame#DropZone:hover {
    background-color: rgba(99, 102, 241, 0.08);
    border-color: #818cf8;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton.btn-primary:hover {
    background-color: #4f46e5;
}

QPushButton.btn-primary:pressed {
    background-color: #4338ca;
}

QPushButton.btn-secondary {
    background-color: #1e293b;
    color: #dae2fd;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton.btn-secondary:hover {
    background-color: #27354a;
    border-color: #475569;
    color: #ffffff;
}

QPushButton.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton.btn-danger:hover {
    background-color: #dc2626;
}

QPushButton.btn-success {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton.btn-success:hover {
    background-color: #059669;
}

/* Input Fields */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0f172a;
    color: #dae2fd;
    border: 1px solid #222a3d;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366f1;
}

/* List Widgets */
QListWidget {
    background-color: #0f172a;
    color: #dae2fd;
    border: 1px solid #222a3d;
    border-radius: 8px;
    padding: 6px;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 0px;
}

QListWidget::item:hover {
    background-color: #1e293b;
    color: #ffffff;
}

QListWidget::item:selected {
    background-color: #27354a;
    color: #c0c1ff;
    font-weight: 600;
}

/* Tables */
QTableWidget {
    background-color: #131b2e;
    color: #dae2fd;
    border: 1px solid #222a3d;
    border-radius: 8px;
    gridline-color: #1e293b;
    selection-background-color: #27354a;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 9px 12px;
    border-bottom: 1px solid #1a233a;
}

QHeaderView::section {
    background-color: #171f33;
    color: #94a3b8;
    border: none;
    border-bottom: 1px solid #28334e;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0b1326;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #222a3d;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b4866;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress Bar */
QProgressBar {
    background-color: #131b2e;
    border: 1px solid #222a3d;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #818cf8);
    border-radius: 7px;
}

/* Badges / Chips */
QLabel.badge-emerald {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-indigo {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-amber {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-rose {
    background-color: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.35);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}
"""
