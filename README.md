# Intelligent Content-Based Application Deduplication & Categorization System (IADCS)

**Problem Code:** JP-001  
**Core Language:** Python 3.12+ / 3.13  
**UI Framework:** PyQt6 (Dark Obsidian-Indigo Glassmorphism)  
**Database:** SQLite with Write-Ahead Logging (WAL)

---

## 🌟 Key Features

1. **Content-First Application Identity**:
   - Applications are identified by their deterministic content manifests and SHA-256 fingerprints, **never** by filename, path, or timestamp alone.
   - Multi-stage pipeline: **Size Filtering ➔ Partial Chunk Hash (Header/Middle/Footer) ➔ Full Streaming SHA-256 ➔ Deterministic Sorted Relative-Path Manifest ➔ Byte-Level Binary Verification**.
2. **Rule-Based Categorization**:
   - Automated categorization supporting customizable priorities, operators (`contains`, `equals`, `regex`, `starts_with`, `ends_with`, `gt`, `lt`), and fields (`name`, `path`, `executable`, `app_type`, `size`).
   - Default categories: Development, Web Development, Database, Security, Graphics/Design, Media, Office/Productivity, Communication, Games, Utilities, Education, System Software, and Other.
3. **Pre-Removal Safety Verification**:
   - Path existence validation, OS protected directory safeguards (blocking `C:\Windows`, `System32`, etc.), and real-time content drift checks before destruction.
   - Non-destructive **Quarantine** mode with complete restore capability, plus Recycle Bin (Trash) and permanent deletion options.
4. **Professional, Minimalist UI & Complete CLI**:
   - Sleek PyQt6 desktop dashboard featuring responsive background workers, multi-stage progress indicators, inventory tables, duplicate review with smart selective checkboxes, rule editor, and JSON reports.
   - CLI commands for automated or headless environments.
5. **Full Auditability & JSON Reports**:
   - Structured JSON audit logging of all scan, discovery, and removal operations.
   - Standardized machine-readable JSON reports.

---

## 🚀 Quick Start

### 1. Installation
Ensure Python 3.12+ is installed, then install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch Desktop GUI
```bash
python main.py
# or
python main.py gui
```

### 3. Command Line Interface (CLI)
```bash
# Scan directories
python main.py scan --path "C:\Applications" --path "D:\Backups"

# List detected duplicate groups
python main.py duplicates

# View categorized application breakdown
python main.py categories

# View configured rules
python main.py rules

# Export machine-readable JSON report
python main.py report --output report.json

# Safely remove/quarantine duplicate application with explicit confirmation
python main.py remove --app-id 2 --action quarantine --confirm
```

---

## 🧪 Running Automated Tests
Run the comprehensive test suite with `pytest`:
```bash
python -m pytest tests/ -v
```
Or with the built-in standalone runner:
```bash
python tests/run_all.py
```

---

## 📁 System Architecture
```text
IADCS/
├── app/
│   ├── config/          # settings.yaml & default_categories.yaml
│   ├── core/            # Dataclasses, types, enums
│   ├── database/        # SQLite schema, WAL connection, repository
│   ├── scanner/         # Traversal, platform detector, application detectors
│   ├── hashing/         # Streaming SHA-256, partial hashing, fingerprints
│   ├── duplicate/       # Candidate matcher, grouping, byte verifier
│   ├── categorization/  # Priority rule engine & category manager
│   ├── removal/         # Safety validator, quarantine manager, removal orchestrator
│   ├── reporting/       # JSON report generator
│   ├── logging/         # Structured JSON audit logger
│   ├── ui/              # PyQt6 Obsidian Dark GUI views & theme
│   ├── cli.py           # Command line interface
│   └── main.py          # Unified entry point
├── tests/               # Unit, integration, safety & reporting test suite
├── main.py              # Root launcher
├── PRD.md               # Product Requirements Document
└── requirements.txt     # Dependencies
```
