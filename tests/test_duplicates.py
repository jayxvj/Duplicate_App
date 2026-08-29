"""Tests for content-based duplicate detection and grouping rules."""
from app.core.types import Application, FileRecord
from app.hashing.fingerprint import generate_application_fingerprint
from app.duplicate.duplicate_detector import DuplicateDetector


def test_exact_duplicate_different_names_and_paths():
    # App 1 in C:/Apps/MyEditor
    f1 = [
        FileRecord(relative_path="editor.exe", absolute_path="C:/Apps/MyEditor/editor.exe", size=5000, sha256="hash_bin_1", is_readable=True),
        FileRecord(relative_path="assets/icon.png", absolute_path="C:/Apps/MyEditor/assets/icon.png", size=200, sha256="hash_img_1", is_readable=True),
    ]
    app1 = Application(name="MyEditor", root_path="C:/Apps/MyEditor", total_size=5200, file_count=2, files=f1)
    app1.content_fingerprint = generate_application_fingerprint(f1)

    # App 2 in D:/Backup/OldApp (Different name & path, identical content)
    f2 = [
        FileRecord(relative_path="editor.exe", absolute_path="D:/Backup/OldApp/editor.exe", size=5000, sha256="hash_bin_1", is_readable=True),
        FileRecord(relative_path="assets/icon.png", absolute_path="D:/Backup/OldApp/assets/icon.png", size=200, sha256="hash_img_1", is_readable=True),
    ]
    app2 = Application(name="OldApp", root_path="D:/Backup/OldApp", total_size=5200, file_count=2, files=f2)
    app2.content_fingerprint = generate_application_fingerprint(f2)

    detector = DuplicateDetector(auto_verify_bytes=False)
    groups = detector.detect_duplicates([app1, app2])

    assert len(groups) == 1
    assert groups[0].application_count == 2
    assert groups[0].reclaimable_size == 5200


def test_partially_shared_files_do_not_create_application_duplicate():
    # App A and App B share a common dll, but different main executables
    f_a = [
        FileRecord(relative_path="app.exe", absolute_path="C:/A/app.exe", size=1000, sha256="hash_exe_A", is_readable=True),
        FileRecord(relative_path="common.dll", absolute_path="C:/A/common.dll", size=2000, sha256="shared_dll_hash", is_readable=True),
    ]
    app_a = Application(name="AppA", root_path="C:/A", total_size=3000, file_count=2, files=f_a)
    app_a.content_fingerprint = generate_application_fingerprint(f_a)

    f_b = [
        FileRecord(relative_path="app.exe", absolute_path="C:/B/app.exe", size=1500, sha256="hash_exe_B", is_readable=True),
        FileRecord(relative_path="common.dll", absolute_path="C:/B/common.dll", size=2000, sha256="shared_dll_hash", is_readable=True),
    ]
    app_b = Application(name="AppB", root_path="C:/B", total_size=3500, file_count=2, files=f_b)
    app_b.content_fingerprint = generate_application_fingerprint(f_b)

    detector = DuplicateDetector(auto_verify_bytes=False)
    groups = detector.detect_duplicates([app_a, app_b])

    assert len(groups) == 0


def test_standalone_single_file_duplicate_different_names():
    # Standalone script/package with different names but identical content
    f1 = [FileRecord(relative_path="backup_tool.py", absolute_path="C:/Tools/backup_tool.py", size=450, sha256="py_script_hash_1", file_type=".py", is_readable=True)]
    app1 = Application(name="backup_tool", root_path="C:/Tools/backup_tool.py", total_size=450, file_count=1, files=f1)
    app1.content_fingerprint = generate_application_fingerprint(f1)

    f2 = [FileRecord(relative_path="copy_tool.py", absolute_path="D:/Scripts/copy_tool.py", size=450, sha256="py_script_hash_1", file_type=".py", is_readable=True)]
    app2 = Application(name="copy_tool", root_path="D:/Scripts/copy_tool.py", total_size=450, file_count=1, files=f2)
    app2.content_fingerprint = generate_application_fingerprint(f2)

    detector = DuplicateDetector(auto_verify_bytes=False)
    groups = detector.detect_duplicates([app1, app2])

    assert len(groups) == 1
    assert groups[0].application_count == 2
    assert groups[0].reclaimable_size == 450


def test_acceptance_same_name_different_content():
    f1 = [FileRecord(relative_path="app.exe", absolute_path="C:/A/app.exe", size=5000, sha256="hash_A", is_readable=True)]
    app1 = Application(name="app", root_path="C:/A/app.exe", total_size=5000, file_count=1, files=f1)
    app1.content_fingerprint = generate_application_fingerprint(f1)

    f2 = [FileRecord(relative_path="app.exe", absolute_path="C:/B/app.exe", size=5000, sha256="hash_B", is_readable=True)]
    app2 = Application(name="app", root_path="C:/B/app.exe", total_size=5000, file_count=1, files=f2)
    app2.content_fingerprint = generate_application_fingerprint(f2)

    detector = DuplicateDetector(auto_verify_bytes=False)
    groups = detector.detect_duplicates([app1, app2])
    assert len(groups) == 0


def test_acceptance_three_identical_copies_and_reference_ranking():
    # Copy 1 in Backup
    f1 = [FileRecord(relative_path="app.exe", absolute_path="D:/Backup/app.exe", size=2000, sha256="hash_shared", is_readable=True)]
    app_backup = Application(name="app", root_path="D:/Backup/app.exe", total_size=2000, file_count=1, files=f1)
    app_backup.content_fingerprint = generate_application_fingerprint(f1)

    # Copy 2 in Program Files (should be chosen as Reference / Keep index 0)
    f2 = [FileRecord(relative_path="app.exe", absolute_path="C:/Program Files/app.exe", size=2000, sha256="hash_shared", is_readable=True)]
    app_installed = Application(name="app", root_path="C:/Program Files/app.exe", total_size=2000, file_count=1, files=f2)
    app_installed.content_fingerprint = generate_application_fingerprint(f2)

    # Copy 3 in Downloads
    f3 = [FileRecord(relative_path="app.exe", absolute_path="C:/Downloads/app.exe", size=2000, sha256="hash_shared", is_readable=True)]
    app_downloads = Application(name="app", root_path="C:/Downloads/app.exe", total_size=2000, file_count=1, files=f3)
    app_downloads.content_fingerprint = generate_application_fingerprint(f3)

    detector = DuplicateDetector(auto_verify_bytes=False)
    groups = detector.detect_duplicates([app_backup, app_installed, app_downloads])

    assert len(groups) == 1
    assert groups[0].application_count == 3
    assert groups[0].reclaimable_size == 4000
    # The reference application at index 0 should be the Program Files installation
    assert "program files" in groups[0].applications[0].root_path.lower()


