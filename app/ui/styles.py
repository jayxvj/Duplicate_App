"""Obsidian Sentinel dark glassmorphism styling for IADCS PyQt6 Desktop UI."""

MAIN_STYLE = """
/* Global Application Style */
QWidget {
    background-color: #0d0e12;
    color: #e3e2e7;
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #121317;
    border-right: 1px solid #1f1f26;
    min-width: 220px;
    max-width: 240px;
}

QLabel#SidebarTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    padding: 16px 12px 4px 12px;
}

QLabel#SidebarSubtitle {
    color: #818cf8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0px 12px 16px 12px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 8px;
}

QPushButton.nav-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #e3e2e7;
}

QPushButton.nav-btn:checked {
    background-color: #1f1f2e;
    color: #c0c1ff;
    font-weight: 600;
    border-left: 3px solid #6366f1;
}

/* Header & Cards */
QFrame.card {
    background-color: #16181f;
    border: 1px solid #232530;
    border-radius: 8px;
    padding: 16px;
}

QLabel.card-title {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.card-value {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
    margin-top: 4px;
}

QLabel.card-subtitle {
    color: #10b981;
    font-size: 12px;
    font-weight: 500;
    margin-top: 2px;
}

/* Primary Action Buttons */
QPushButton.btn-primary {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
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
    background-color: #1f1f26;
    color: #e3e2e7;
    border: 1px solid #2d2e38;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton.btn-secondary:hover {
    background-color: #2a2b36;
    border-color: #3f404e;
}

QPushButton.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton.btn-danger:hover {
    background-color: #dc2626;
}

QPushButton.btn-success {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton.btn-success:hover {
    background-color: #059669;
}

/* Input Fields */
QLineEdit, QComboBox, QSpinBox {
    background-color: #121317;
    color: #e3e2e7;
    border: 1px solid #282a36;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366f1;
}

/* Tables */
QTableWidget {
    background-color: #121317;
    color: #e3e2e7;
    border: 1px solid #1f2029;
    border-radius: 6px;
    gridline-color: #1a1b24;
    selection-background-color: #26273b;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #181922;
}

QHeaderView::section {
    background-color: #16171e;
    color: #94a3b8;
    border: none;
    border-bottom: 1px solid #232530;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0d0e12;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #242632;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b3e4f;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress Bar */
QProgressBar {
    background-color: #16181f;
    border: 1px solid #232530;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 5px;
}

/* Badges / Chips */
QLabel.badge-emerald {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-indigo {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-amber {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
"""
