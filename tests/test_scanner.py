"""Tests for directory scanning, exclusions, and application boundary detection."""
from pathlib import Path
from app.scanner.directory_scanner import DirectoryScanner
from app.scanner.application_detector import CompositeApplicationDetector


def test_directory_scanner_recursive_and_exclusions(tmp_path: Path):
    app_dir = tmp_path / "DemoApp"
    app_dir.mkdir()
    (app_dir / "app.exe").write_bytes(b"MZ_EXE_HEADER_DATA")
    (app_dir / "readme.txt").write_text("Hello World")

    sub_dir = app_dir / "lib"
    sub_dir.mkdir()
    (sub_dir / "helper.dll").write_bytes(b"DLL_DATA")

    # Excluded folder inside app
    excl_dir = app_dir / ".git"
    excl_dir.mkdir()
    (excl_dir / "config").write_text("git config")

    # Non-application folder in the same root (e.g. photos/documents)
    doc_dir = tmp_path / "PersonalDocuments"
    doc_dir.mkdir()
    (doc_dir / "notes.txt").write_text("Plain text notes")
    (doc_dir / "photo.png").write_bytes(b"PNG_DATA")

    scanner = DirectoryScanner(exclusions=[".git"])
    apps = scanner.scan_directories([tmp_path])

    # ONLY DemoApp must be discovered as an application, PersonalDocuments must NOT be an application
    assert len(apps) == 1
    discovered = apps[0]
    assert discovered.name == "app"
    assert discovered.file_count == 3


def test_detector_identifies_python_and_windows_apps(tmp_path: Path):
    detector = CompositeApplicationDetector()

    py_app = tmp_path / "PyApp"
    py_app.mkdir()
    (py_app / "pyvenv.cfg").write_text("home = C:/Python")
    res = detector.detect_application(py_app)
    assert res is not None
    app_type, name = res
    assert app_type.value == "python_app"

    win_app = tmp_path / "WinTool"
    win_app.mkdir()
    (win_app / "wintool.exe").write_bytes(b"EXE")
    res = detector.detect_application(win_app)
    assert res is not None
    app_type, name = res
    assert app_type.value == "windows_portable"

    # Non-app directory
    plain_dir = tmp_path / "PlainFolder"
    plain_dir.mkdir()
    (plain_dir / "file.csv").write_text("a,b,c")
    assert detector.detect_application(plain_dir) is None


def test_detector_handles_standalone_and_script_candidates(tmp_path: Path):
    detector = CompositeApplicationDetector()

    # Standalone executable
    exe_file = tmp_path / "tool.exe"
    exe_file.write_bytes(b"MZ_BIN")
    res = detector.detect_application(exe_file)
    assert res is not None
    assert res[0].value == "standalone_binary"
    assert res[1] == "tool"

    # Python module init marker -> NOT an application
    init_py = tmp_path / "__init__.py"
    init_py.write_text("# empty init")
    assert detector.detect_application(init_py) is None

    # Standalone script files -> detected as script candidates
    helper_py = tmp_path / "helper.py"
    helper_py.write_text("def add(a, b):\n    return a + b\n")
    res = detector.detect_application(helper_py)
    assert res is not None
    assert res[0].value == "python_app"
    assert res[1] == "helper"


def test_scan_discovers_standalone_duplicate_executables(tmp_path: Path):
    from app.duplicate.candidate_matcher import CandidateMatcher
    from app.duplicate.duplicate_detector import DuplicateDetector

    # User scan directory containing 2 duplicate executables
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir()
    (downloads_dir / "installer_v1.exe").write_bytes(b"EXECUTABLE_BYTE_DATA_X" * 100)
    (downloads_dir / "installer_copy.exe").write_bytes(b"EXECUTABLE_BYTE_DATA_X" * 100)

    scanner = DirectoryScanner()
    apps = scanner.scan_directories([downloads_dir])

    # Must discover both .exe files as independent standalone binary applications
    assert len(apps) == 2
    assert all(a.app_type.value == "standalone_binary" for a in apps)

    matcher = CandidateMatcher()
    apps = matcher.process_applications(apps)

    detector = DuplicateDetector(auto_verify_bytes=True)
    groups = detector.detect_duplicates(apps)

    # Must find 1 duplicate group containing both executables
    assert len(groups) == 1
    assert groups[0].application_count == 2
    assert groups[0].reclaimable_size == len(b"EXECUTABLE_BYTE_DATA_X" * 100)



