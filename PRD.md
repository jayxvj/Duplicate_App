# PRD — Intelligent Content-Based Application Deduplication & Categorization System

**Problem Code:** JP-001  
**Programming Language:** Python 3.12.x  
**Document Version:** 1.0  
**Status:** Implementation-Ready  
**Target:** Local desktop application with optional CLI mode

---

## 1. Product Overview

### 1.1 Product Name

**Intelligent Application Deduplication & Categorization System**

### 1.2 Purpose

Build a Python application that discovers applications in user-selected directories, identifies duplicate applications using their actual content rather than filename, timestamp, or file type, automatically categorizes applications using configurable rules, presents duplicate groups for user review, safely removes user-selected duplicates, and generates audit logs and reports.

The product is a **content-based application management tool**, not merely a filename-based duplicate-file finder.

### 1.3 Core Principle

> **Application identity must be determined primarily from content. Metadata may be used for discovery and optimization, but never as the sole basis for declaring an application a duplicate.**

---

# 2. Problem Statement

Users may have multiple copies of the same application distributed across different directories, drives, backups, extracted folders, or installation locations.

The copies may have:

- Different filenames
- Different paths
- Different timestamps
- Different directory names
- Different file extensions in some cases
- Different metadata

A traditional duplicate finder based on filenames or timestamps cannot reliably identify these duplicates.

The system must therefore answer:

> **Are these two application installations/content trees actually identical or equivalent according to their content?**

The solution must also organize discovered applications into predefined categories and allow users to safely select duplicates for removal.

---

# 3. Goals

## 3.1 Primary Goals

1. Recursively scan user-selected directories.
2. Discover application candidates.
3. Analyze application file structures and contents.
4. Generate content fingerprints.
5. Detect exact duplicate application content.
6. Avoid using filename, timestamp, or file type as the primary duplicate criterion.
7. Automatically categorize applications using configurable rules.
8. Display duplicate groups clearly.
9. Allow users to select which duplicate applications to remove.
10. Prevent accidental deletion through validation and confirmation.
11. Record every scan, detection, categorization, and removal operation.
12. Generate useful reports.
13. Handle small and large application structures efficiently.
14. Provide a clean desktop UI and optional CLI workflow.

## 3.2 Secondary Goals

- Support configurable scan exclusions.
- Cache hashes to avoid unnecessary reprocessing.
- Support resumable/repeated scans.
- Provide storage-recovery estimates.
- Make the architecture extensible to additional operating systems and application formats.
- Keep the MVP completely local so application contents do not need to leave the user's machine.

---

# 4. Non-Goals

The MVP will NOT:

1. Automatically delete duplicates without user approval.
2. Treat similar filenames as proof of duplication.
3. Treat identical file sizes as proof of duplication.
4. Use AI/ML as the primary duplicate detector.
5. Attempt to determine semantic similarity between different application versions.
6. Replace the operating system's package manager.
7. Automatically uninstall registered applications through OS-specific uninstallers unless implemented as a future extension.
8. Upload application files or hashes to a cloud service.
9. Modify unrelated system files.
10. Delete protected operating-system components without explicit safeguards.

---

# 5. Users

## Primary User

A desktop user who wants to:

- Find redundant application installations.
- Recover disk space.
- Understand what applications exist on selected directories.
- Organize applications into categories.
- Safely remove selected redundant copies.

## Secondary User

A technical user who wants CLI access and machine-readable reports.

---

# 6. Functional Requirements

## FR-001 — Directory Configuration

The system SHALL allow users to:

- Add directories.
- Remove directories.
- Scan multiple directories.
- Configure excluded directories.
- Save scan configuration.

Example:

```text
C:\Program Files
C:\Program Files (x86)
C:\Users\<user>\AppData\Local
D:\Applications
```

The application SHALL validate that configured paths exist and are readable before scanning.

---

## FR-002 — Recursive File Scanning

The scanner SHALL recursively traverse configured directories.

For every encountered file, it should collect:

- Absolute path
- Relative path
- File size
- Extension/type
- Readability
- Application association
- Hash status

The scanner SHALL handle:

- Missing files
- Permission errors
- Locked files
- Symbolic links
- Very large files
- Empty files

without crashing the complete scan.

---

## FR-003 — Application Discovery

The system SHALL identify application candidates rather than treating every file as an independent application.

The discovery layer SHALL support an extensible detector architecture:

```text
ApplicationDetector
├── WindowsApplicationDetector
├── JavaApplicationDetector
├── PythonApplicationDetector
└── GenericApplicationDetector
```

For the MVP, the implementation SHALL prioritize the host operating system while keeping the detector interface platform-independent.

Application indicators may include:

- Executables
- Application bundles/directories
- JAR/application manifests
- OS application metadata
- Executable entry points
- Installation structures

---

# 7. Content-Based Duplicate Detection

## FR-004 — Content-First Detection

The system SHALL NOT declare applications duplicates solely because they have:

- The same filename
- The same timestamp
- The same extension
- The same directory name
- The same path pattern

These fields may only support discovery, filtering, or categorization.

---

## FR-005 — Multi-Stage Duplicate Detection Pipeline

The required detection pipeline is:

```text
Application Discovery
        ↓
File Inventory
        ↓
File Size Grouping
        ↓
Partial/Chunk Fingerprint
        ↓
Full SHA-256
        ↓
Application Content Manifest
        ↓
Application Fingerprint
        ↓
Byte-Level Verification
        ↓
Confirmed Duplicate
```

### Stage 1 — Size Filtering

Files with different sizes SHALL NOT be treated as exact binary duplicates.

Size is a performance optimization only.

### Stage 2 — Partial Hashing

For sufficiently large files, the system MAY hash selected chunks such as:

- Beginning
- Middle
- End

to eliminate obvious non-matches before calculating a complete SHA-256 digest.

### Stage 3 — SHA-256

The system SHALL calculate SHA-256 for candidate files.

Example:

```text
File A → SHA-256 → ABC123...
File B → SHA-256 → ABC123...
```

Matching hashes create a candidate match.

### Stage 4 — Byte Verification

Before destructive removal, matching content SHALL be optionally or mandatorily verified byte-by-byte for the final duplicate decision.

---

# 8. Application Content Fingerprinting

Individual matching files SHALL NOT automatically imply that entire applications are duplicates.

Example:

```text
Application A
├── app.exe
├── common.dll
└── config.json

Application B
├── another.exe
├── common.dll
└── different.json
```

Only `common.dll` is duplicated.

The applications are NOT automatically duplicates.

The system SHALL construct an application-level content manifest.

Conceptual structure:

```text
Application
│
├── Relative File Path
├── File Size
├── SHA-256
├── File Type
└── Content Attributes
        ↓
Sorted Application Manifest
        ↓
Application Content Fingerprint
```

The manifest SHALL be deterministic so that the same application content produces the same fingerprint even when installed under different root directories.

The root installation path SHALL NOT be included as an identity component.

---

# 9. Duplicate Groups

The duplicate engine SHALL group confirmed application duplicates.

Example:

```text
Duplicate Group #001

Application A
Path: C:\Apps\AppA
Size: 1.8 GB
Fingerprint: ABC123

Application B
Path: D:\Backup\AppB
Size: 1.8 GB
Fingerprint: ABC123

Match: Exact Content
Potential Recovery: 1.8 GB
```

Each group SHALL contain:

- Group ID
- Applications
- Application fingerprints
- Matching criteria
- Total size
- Reclaimable size
- Verification status
- Detection timestamp

---

# 10. Rule-Based Categorization

## FR-006 — Configurable Rules

The categorization engine SHALL support user-managed predefined rules.

Rules SHALL be stored in YAML or JSON.

Example:

```yaml
categories:
  - name: Development
    priority: 100
    rules:
      - field: path
        operator: contains
        value: developer

      - field: executable
        operator: contains
        value: code

  - name: Media
    priority: 80
    rules:
      - field: executable
        operator: contains
        value: player
```

---

# 11. Categorization Inputs

Rules may evaluate:

- Application name
- Executable name
- Installation path
- File extensions
- Manifest information
- Basic content-derived indicators
- Platform
- Application type

Rules SHALL NOT require uploading application content externally.

---

# 12. Category Priority

An application may match multiple categories.

The system SHALL resolve conflicts through rule priority.

Example:

```text
Development Rule → TRUE
Utilities Rule → TRUE
Media Rule → FALSE

Highest priority:
Development
```

If no rule matches:

```text
Category = Other / Uncategorized
```

---

# 13. Default Categories

The MVP SHOULD provide:

```text
Development
Office/Productivity
Graphics/Design
Media
Communication
Security
Utilities
Education
Games
Database
Web Development
System Software
Other
```

Users SHALL be able to modify categories and rules.

---

# 14. Application Inventory

The system SHALL maintain an inventory containing:

```text
Application ID
Name
Root Path
Platform
Application Type
Total Size
File Count
Content Fingerprint
Category
Scan ID
```

Individual files SHALL maintain:

```text
File ID
Application ID
Relative Path
Absolute Path
Size
SHA-256
File Type
```

---

# 15. Duplicate Removal

## FR-007 — User-Controlled Removal

The system SHALL NEVER automatically delete a detected duplicate immediately.

Required workflow:

```text
Scan
 ↓
Detect
 ↓
Show Duplicate Groups
 ↓
User Reviews
 ↓
User Selects
 ↓
Safety Validation
 ↓
Confirmation
 ↓
Quarantine/Delete
 ↓
Verification
 ↓
Audit Log
```

---

# 16. Removal Safety

Before deletion, the system SHALL verify:

1. The selected path still exists.
2. The path belongs to the detected application.
3. The content fingerprint has not unexpectedly changed.
4. The application is still classified as a duplicate.
5. The user explicitly selected the item.
6. The operation is not targeting an excluded/protected path.

The system SHALL display a final confirmation containing:

- Application name
- Location
- Size
- Duplicate counterpart(s)
- Potential space recovered
- Number of files affected

---

# 17. Quarantine

The architecture SHOULD support quarantine as the preferred removal mechanism.

```text
Original
   ↓
Quarantine
   ↓
Verification
   ↓
Permanent Delete
```

If quarantine is not implemented in the first MVP, direct deletion MAY be used only with explicit confirmation and detailed logging.

---

# 18. Protected Paths

The application SHALL provide configurable exclusions for:

- OS system directories
- Critical application directories
- User-defined protected locations
- Symbolic-link targets where unsafe
- Other administrator-defined paths

The system SHALL fail safely when permission is insufficient.

---

# 19. Reporting

The system SHALL produce:

## Scan Report

- Scan locations
- Files scanned
- Applications found
- Scan duration
- Errors
- Skipped files

## Duplicate Report

- Duplicate groups
- Applications per group
- Fingerprints
- Matching status
- Reclaimable space

## Categorization Report

```text
Development: 12
Utilities: 21
Media: 8
Security: 5
Games: 7
Other: 4
```

## Removal Report

- Selected applications
- Successful removals
- Failed removals
- Reclaimed storage
- Errors
- Timestamp

Reports SHALL support JSON as the primary machine-readable format.

---

# 20. Logging

The application SHALL use structured logging.

Example:

```json
{
  "operation": "duplicate_removal",
  "application": "ExampleApp",
  "path": "C:/Apps/ExampleApp",
  "content_hash": "abc123...",
  "size": 1834000000,
  "status": "success"
}
```

Log events SHOULD include:

- Scan started
- Scan completed
- Application discovered
- Hash calculated
- Duplicate detected
- Category assigned
- Removal requested
- Removal completed
- Removal failed
- Permission error
- Unexpected error

---

# 21. User Interface

The desktop UI SHALL contain:

## Dashboard

Display:

- Applications discovered
- Duplicate groups
- Potential space recovery
- Categories
- Last scan
- Scan status

## Scan Configuration

- Add path
- Remove path
- Exclusions
- Start scan
- Cancel scan
- Progress indicator

## Application Inventory

Columns:

```text
Name | Category | Location | Size | Files | Fingerprint
```

## Duplicate View

Columns:

```text
Group | Application | Location | Size | Match | Select
```

## Categories View

Applications grouped by category.

## Rules View

Users can:

- Add rule
- Edit rule
- Delete rule
- Enable/disable rule
- Change priority
- Add category

## Reports View

Users can view/export generated reports.

---

# 22. CLI Requirements

The system SHOULD expose CLI commands.

Example:

```bash
python main.py scan --path "C:\Apps"
```

```bash
python main.py duplicates
```

```bash
python main.py categories
```

```bash
python main.py rules --list
```

```bash
python main.py report --format json
```

Removal SHALL require explicit confirmation:

```bash
python main.py remove --group 12 --confirm
```

The CLI SHALL NOT silently delete files.

---

# 23. System Architecture

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │ UI / CLI Layer  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Application Core│
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
   │ Scan Manager│  │ Hash Engine │  │ Rule Engine  │
   └──────┬──────┘  └──────┬──────┘  └───────┬──────┘
          │                 │                 │
          ▼                 ▼                 ▼
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
   │ Application │  │ Fingerprint │  │ Categories   │
   │ Discovery   │  │ Generator   │  │              │
   └──────┬──────┘  └──────┬──────┘  └──────────────┘
          │                 │
          └────────┬────────┘
                   ▼
           ┌─────────────────┐
           │ Duplicate Engine│
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Duplicate Groups│
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ User Approval   │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Removal Manager │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Logs & Reports  │
           └─────────────────┘

                   ▲
                   │
             ┌─────┴─────┐
             │   SQLite  │
             └───────────┘
```

---

# 24. Module Architecture

```text
app/
│
├── main.py
│
├── scanner/
│   ├── directory_scanner.py
│   ├── application_detector.py
│   └── platform_detector.py
│
├── analyzer/
│   ├── file_analyzer.py
│   ├── manifest_parser.py
│   └── content_analyzer.py
│
├── hashing/
│   ├── partial_hash.py
│   ├── sha256.py
│   └── fingerprint.py
│
├── duplicate/
│   ├── candidate_matcher.py
│   ├── duplicate_detector.py
│   └── verifier.py
│
├── categorization/
│   ├── rule_loader.py
│   ├── rule_engine.py
│   └── category_manager.py
│
├── removal/
│   ├── removal_manager.py
│   ├── quarantine.py
│   └── safety_validator.py
│
├── database/
│   ├── database.py
│   ├── models.py
│   └── repository.py
│
├── reporting/
│   ├── scan_report.py
│   ├── duplicate_report.py
│   ├── categorization_report.py
│   └── removal_report.py
│
├── logging/
│   └── audit_logger.py
│
├── ui/
│   ├── dashboard.py
│   ├── scan_view.py
│   ├── duplicate_view.py
│   ├── category_view.py
│   └── rules_view.py
│
├── config/
│   ├── settings.yaml
│   └── categories.yaml
│
└── tests/
    ├── test_scanner.py
    ├── test_hashing.py
    ├── test_duplicates.py
    ├── test_rules.py
    └── test_removal.py
```

---

# 25. Data Model

## Application

```text
id
name
root_path
platform
application_type
total_size
file_count
content_fingerprint
category
scan_id
created_at
updated_at
```

## FileRecord

```text
id
application_id
relative_path
absolute_path
size
sha256
file_type
is_readable
```

## DuplicateGroup

```text
id
fingerprint
application_count
total_size
reclaimable_size
verification_status
created_at
```

## Rule

```text
id
category
field
operator
value
priority
enabled
```

## OperationLog

```text
id
operation
application_id
path
hash
status
error
timestamp
```

---

# 26. Recommended Technology Stack

## Primary

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12.x |
| File System | pathlib / os | Standard Library |
| Hashing | hashlib | Standard Library |
| Configuration | JSON + YAML | JSON + PyYAML 6.x |
| Rule Engine | rule-engine | Current stable compatible release |
| Database | SQLite | 3.x |
| Database API | sqlite3 | Standard Library |
| GUI | Tkinter | Standard Library |
| Alternative GUI | PySide6 | 6.x |
| Logging | logging | Standard Library |
| Testing | pytest | 8.x |
| Packaging | PyInstaller | Current stable |

## Why Python?

Python is preferred because the PS is fundamentally a local filesystem-processing problem. It provides mature filesystem APIs, hashing support, rapid development, simple configuration handling, and an accessible testing/tooling ecosystem without requiring unnecessary backend infrastructure.

---

# 27. Java Alternative

A compliant Java implementation MAY use:

| Component | Technology |
|---|---|
| Language | Java |
| JDK | JDK 21 LTS |
| File Handling | Apache Commons IO |
| Hashing | Apache Commons Codec |
| Rule Engine | Drools |
| Database | SQLite |
| GUI | JavaFX |
| Build | Maven |
| Testing | JUnit 5 |

Java is technically valid, but Python is the preferred implementation for this project because it reduces implementation complexity while fully supporting the required filesystem, hashing, rule, database, and reporting workflows.

---

# 28. Performance Requirements

## PR-001

The scanner SHALL process files using streaming/chunked reads rather than loading complete large files into memory.

## PR-002

SHA-256 SHALL be calculated incrementally.

Example:

```text
Read 4 MB chunk
 ↓
Update SHA-256
 ↓
Read next chunk
 ↓
Update SHA-256
 ↓
...
 ↓
Final digest
```

## PR-003

The system SHOULD avoid hashing files that can be eliminated through safe preliminary checks.

Recommended:

```text
Size
 ↓
Partial hash
 ↓
Full hash
```

## PR-004

Independent file hashing SHOULD support controlled concurrency.

Use Python's:

```text
concurrent.futures
```

with bounded worker counts.

## PR-005

The application SHALL remain responsive during scans.

The UI scan operation SHALL run outside the main UI event loop.

---

# 29. Reliability Requirements

The application SHALL:

- Continue scanning when an individual file cannot be read.
- Record permission failures.
- Handle deleted/moved files gracefully.
- Detect files changing during hashing.
- Avoid corrupting the database after unexpected termination.
- Preserve logs after failed operations.
- Validate paths before destructive operations.

---

# 30. Security Requirements

## SEC-001

The application SHALL operate locally by default.

## SEC-002

No application content SHALL be uploaded externally.

## SEC-003

Deletion SHALL require explicit user action.

## SEC-004

Protected/excluded directories SHALL be respected.

## SEC-005

The system SHALL verify duplicate state before deletion.

## SEC-006

Logs SHALL not unnecessarily expose sensitive file contents.

Only paths, hashes, sizes, statuses, and required metadata should be logged.

---

# 31. Input → Processing → Output

## Input

```text
1. Scan directories
2. Excluded directories
3. Categorization rules
4. User configuration
5. User-selected duplicates
```

## Processing

```text
Directory scan
      ↓
Application discovery
      ↓
File inventory
      ↓
Size filtering
      ↓
Partial hashing
      ↓
SHA-256
      ↓
Application manifest
      ↓
Application fingerprint
      ↓
Duplicate grouping
      ↓
Rule-based categorization
      ↓
User review
      ↓
Safety validation
      ↓
Removal
```

## Output

```text
1. Application inventory
2. Duplicate groups
3. Categories
4. Storage recovery estimate
5. Removal results
6. JSON reports
7. Audit logs
```

---

# 32. Example End-to-End Scenario

### Input

User selects:

```text
C:\Applications
D:\Backup\Applications
```

### Discovery

System finds:

```text
AppA
AppB
AppC
AppD
```

### Content analysis

```text
AppA fingerprint = ABC123
AppB fingerprint = XYZ789
AppC fingerprint = ABC123
AppD fingerprint = LMN456
```

### Duplicate detection

```text
AppA == AppC
```

because their complete application content fingerprints match.

### Categorization

```text
AppA → Development
AppB → Media
AppC → Development
AppD → Utilities
```

### User interface

```text
Duplicate Group #1

☐ AppA
☑ AppC

Potential recovery: 1.8 GB
```

### Removal

User confirms.

System:

```text
Validate
 ↓
Remove/Quarantine AppC
 ↓
Verify
 ↓
Log
```

### Output

```text
Removed: AppC
Reclaimed: 1.8 GB
Status: SUCCESS
```

---

# 33. Duplicate Detection Rules

The implementation SHALL follow these principles:

### Rule 1

Same filename ≠ duplicate.

### Rule 2

Same path ≠ duplicate identity.

### Rule 3

Same timestamp ≠ duplicate.

### Rule 4

Same file size ≠ duplicate.

### Rule 5

Same individual file hash ≠ duplicate application.

### Rule 6

Same complete application content fingerprint = candidate exact duplicate.

### Rule 7

Final destructive operation requires verification.

---

# 34. Near-Duplicate Policy

The MVP SHALL distinguish exact duplicates from near-duplicates.

Example:

```text
Application A v1.0
Application A v1.1
```

If their content differs:

```text
Exact duplicate = NO
```

They SHALL NOT be automatically removed.

A future version MAY add:

```text
Version similarity
Semantic similarity
Modified-content detection
```

but such functionality is outside the MVP.

---

# 35. Acceptance Criteria

## AC-001 — Scanning

**Given** a configured directory  
**When** the user starts a scan  
**Then** the application recursively discovers readable application candidates.

## AC-002 — Filename Independence

**Given** two applications with different filenames  
**When** their complete content is identical  
**Then** they can be identified as duplicates.

## AC-003 — Timestamp Independence

**Given** identical application content with different timestamps  
**When** scanned  
**Then** timestamps do not prevent duplicate detection.

## AC-004 — Content Difference

**Given** two applications with different content  
**When** scanned  
**Then** they are not classified as exact duplicates solely because their names or sizes match.

## AC-005 — Application-Level Detection

**Given** two applications sharing only some files  
**When** scanned  
**Then** they are not incorrectly classified as duplicate applications.

## AC-006 — Categorization

**Given** an application and matching categorization rules  
**When** analysis completes  
**Then** the application is assigned to the highest-priority matching category.

## AC-007 — Uncategorized Application

**Given** an application matching no rules  
**When** categorization completes  
**Then** it is assigned to `Other` or `Uncategorized`.

## AC-008 — User Approval

**Given** detected duplicates  
**When** the user has not selected an item  
**Then** the system does not delete it.

## AC-009 — Removal

**Given** a user-selected duplicate  
**When** safety validation and confirmation succeed  
**Then** the selected application is removed or quarantined.

## AC-010 — Logging

**Given** any removal operation  
**When** it succeeds or fails  
**Then** an audit log entry is created.

## AC-011 — Reporting

**Given** a completed scan  
**When** the user requests a report  
**Then** the system generates a machine-readable report containing scan, duplicate, category, and storage information.

## AC-012 — Error Handling

**Given** a file that cannot be read  
**When** the scanner encounters it  
**Then** the scanner logs the error and continues where possible.

---

# 36. Testing Strategy

## Unit Tests

Test:

- File traversal
- Size filtering
- Partial hashing
- SHA-256 calculation
- Application fingerprint generation
- Manifest sorting
- Duplicate grouping
- Rule evaluation
- Category priority
- Safety validation
- Report generation

## Integration Tests

Test:

```text
Directory
 ↓
Discovery
 ↓
Hashing
 ↓
Duplicate Detection
 ↓
Categorization
 ↓
Database
 ↓
Report
```

## Safety Tests

Test:

- Wrong path
- Missing path
- Changed file
- Permission denied
- Protected directory
- User cancellation
- Failed deletion
- Duplicate state changed after scan

## Performance Tests

Measure:

- Files/second
- Bytes/second
- Memory consumption
- Hashing time
- Database write time
- Scan time for small/medium/large application trees

---

# 37. MVP Scope

The first implementation SHALL include:

### Must Have

- [x] Directory selection
- [x] Recursive scanning
- [x] Application discovery
- [x] File inventory
- [x] Size filtering
- [x] SHA-256 hashing
- [x] Application fingerprinting
- [x] Duplicate grouping
- [x] Configurable categorization rules
- [x] Application categories
- [x] Duplicate review UI
- [x] User-controlled removal
- [x] Safety confirmation
- [x] Logging
- [x] JSON reporting
- [x] SQLite persistence
- [x] Unit tests

### Should Have

- [ ] Partial/chunk hashing optimization
- [ ] Quarantine
- [ ] CLI
- [ ] Hash caching
- [ ] Scan cancellation
- [ ] Progress reporting

### Future

- [ ] Near-duplicate/version similarity
- [ ] Advanced application manifest parsers
- [ ] OS package-manager integration
- [ ] Scheduled scans
- [ ] Cross-machine inventory
- [ ] Optional advanced similarity/ML module

---

# 38. Recommended Implementation Order

## Phase 1 — Foundation

1. Create Python project.
2. Create configuration system.
3. Create SQLite schema.
4. Implement logging.
5. Implement tests.

## Phase 2 — Scanner

1. Directory scanner.
2. Recursive traversal.
3. Permission handling.
4. Application detector.
5. File inventory.

## Phase 3 — Content Fingerprinting

1. Size filtering.
2. Streaming SHA-256.
3. Partial hashing.
4. Application manifest.
5. Deterministic application fingerprint.
6. Byte verification.

## Phase 4 — Duplicate Engine

1. Candidate matching.
2. Duplicate groups.
3. Reclaimable-space calculation.
4. Verification status.

## Phase 5 — Categorization

1. YAML/JSON rule loader.
2. Rule evaluator.
3. Priority handling.
4. Category manager.
5. Default rules.

## Phase 6 — UI

1. Dashboard.
2. Scan screen.
3. Inventory.
4. Duplicate screen.
5. Category screen.
6. Rule editor.
7. Reports.

## Phase 7 — Safe Removal

1. Safety validator.
2. User confirmation.
3. Quarantine/delete.
4. Post-removal verification.
5. Audit logs.

## Phase 8 — QA & Packaging

1. Unit testing.
2. Integration testing.
3. Performance testing.
4. Security testing.
5. Error-path testing.
6. PyInstaller packaging.
7. End-to-end demonstration.

---

# 39. Key Design Decision

The project SHALL implement the following as the canonical duplicate-detection strategy:

```text
             FILESYSTEM
                 │
                 ▼
        APPLICATION DISCOVERY
                 │
                 ▼
           FILE INVENTORY
                 │
                 ▼
          SIZE FILTERING
                 │
                 ▼
         PARTIAL HASHING
                 │
                 ▼
             SHA-256
                 │
                 ▼
      APPLICATION MANIFEST
                 │
                 ▼
     DETERMINISTIC FINGERPRINT
                 │
                 ▼
        DUPLICATE CANDIDATES
                 │
                 ▼
       BYTE-LEVEL VERIFICATION
                 │
                 ▼
       CONFIRMED DUPLICATES
```

This approach combines efficiency with strong content-based identification.

---

# 40. Final Product Definition

The completed product SHALL be capable of answering four questions:

### 1. What applications exist?

```text
Application Inventory
```

### 2. Which applications are actually duplicates?

```text
Content-Based Duplicate Groups
```

### 3. Where does each application belong?

```text
Rule-Based Categories
```

### 4. What can safely be removed?

```text
User-Approved Removal + Audit Report
```

The final system therefore provides:

```text
             DISCOVER
                ↓
             ANALYZE
                ↓
             FINGERPRINT
                ↓
              DETECT
                ↓
            CATEGORIZE
                ↓
              REVIEW
                ↓
          SAFELY REMOVE
                ↓
             REPORT
```

---

# 41. Definition of Done

The project is considered complete when:

- A user can configure one or more scan directories.
- The system discovers application candidates.
- Files are analyzed using content rather than filename/timestamp identity.
- SHA-256 content fingerprints are generated.
- Complete application fingerprints can identify exact duplicate application content across different locations/names.
- Shared individual files do not automatically cause false application-level duplicate classifications.
- Applications are automatically categorized using configurable rules.
- Duplicate groups are displayed with enough information for a user to make a decision.
- No duplicate is removed without explicit user selection and confirmation.
- Removal is validated and logged.
- Scan, duplicate, categorization, and removal reports can be generated.
- Permission and filesystem errors do not crash the complete scan.
- Large files are processed using streaming/chunked hashing.
- The project has automated tests for the critical detection, categorization, and removal logic.
- The application can be packaged and executed on the target desktop environment.

---

# 42. Final Architecture Decision Summary

| Area | Final Decision |
|---|---|
| Language | **Python 3.12.x** |
| Application Type | Local desktop + optional CLI |
| Duplicate Basis | **Application content** |
| Primary Hash | **SHA-256** |
| Optimization | Size → partial hash → full hash |
| Final Verification | Byte-level verification |
| Application Identity | Deterministic content manifest/fingerprint |
| Categorization | JSON/YAML configurable rules |
| Rule Priority | Explicit priority |
| Persistence | SQLite |
| UI | Tkinter initially; PySide6 acceptable alternative |
| Logging | Python logging + structured records |
| Reports | JSON |
| Removal | User-selected + validated |
| Safety | Quarantine preferred |
| AI/ML | Not used for core MVP |
| Cloud | Not required |
| Primary Objective | Accurate, efficient, safe application deduplication |

---

## Research Basis

The architecture is consistent with established deduplication approaches that use cryptographic content fingerprints to identify redundant content independently of superficial file attributes. SHA-256 is preferred in this design over MD5 as the primary fingerprint because stronger collision resistance is desirable for a destructive file-management workflow. Recent duplicate-file work also describes recursive traversal, cryptographic hashing, duplicate grouping, reporting, and storage-recovery estimation as practical components of such systems.

The research should inform the implementation but does not replace application-level verification and safety controls.

