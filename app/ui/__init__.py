# app/ui/__init__.py
"""User interface package for IADCS."""
try:
    from app.ui.app_window import MainWindow, launch_gui
except ImportError:
    pass

try:
    from app.ui.app import AppWindow
except ImportError:
    pass
