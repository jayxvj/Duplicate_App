# ==============================================================================
# Dockerfile for IADCS (Intelligent Application Deduplication & Categorization System)
# Supports CLI mode, Headless Test Execution, and X11 GUI forwarding
# ==============================================================================

FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen

WORKDIR /app

# Install OS-level system dependencies required for PyQt6 GUI & SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libx11-xcb1 \
    libfontconfig1 \
    libxrender1 \
    libxi6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Run test suite to verify container build integrity
RUN pytest

# Default entrypoint runs the CLI or GUI based on arguments
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
