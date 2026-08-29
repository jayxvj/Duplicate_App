"""Self-contained test runner for IADCS test suite."""
import sys
import tempfile
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_hashing import (
    test_sha256_streaming,
    test_partial_hash_small_and_large,
    test_application_fingerprint_deterministic_and_path_independent,
)
from tests.test_scanner import (
    test_directory_scanner_recursive_and_exclusions,
    test_detector_identifies_python_and_windows_apps,
)
from tests.test_duplicates import (
    test_exact_duplicate_different_names_and_paths,
    test_partially_shared_files_do_not_create_application_duplicate,
)
from tests.test_categorization import (
    test_rule_priority_resolution,
    test_rule_fallback_to_other,
    test_rule_operators_regex_and_equals,
)
from tests.test_removal_safety import (
    test_safety_validator_missing_path,
    test_safety_validator_detects_drift,
    test_quarantine_and_restore_round_trip,
)
from tests.test_reports import test_report_generator_schema_and_export


def main():
    test_funcs = [
        ("test_sha256_streaming", test_sha256_streaming, True),
        ("test_partial_hash_small_and_large", test_partial_hash_small_and_large, True),
        ("test_application_fingerprint_deterministic_and_path_independent", test_application_fingerprint_deterministic_and_path_independent, False),
        ("test_directory_scanner_recursive_and_exclusions", test_directory_scanner_recursive_and_exclusions, True),
        ("test_detector_identifies_python_and_windows_apps", test_detector_identifies_python_and_windows_apps, True),
        ("test_exact_duplicate_different_names_and_paths", test_exact_duplicate_different_names_and_paths, False),
        ("test_partially_shared_files_do_not_create_application_duplicate", test_partially_shared_files_do_not_create_application_duplicate, False),
        ("test_rule_priority_resolution", test_rule_priority_resolution, False),
        ("test_rule_fallback_to_other", test_rule_fallback_to_other, False),
        ("test_rule_operators_regex_and_equals", test_rule_operators_regex_and_equals, False),
        ("test_safety_validator_missing_path", test_safety_validator_missing_path, True),
        ("test_safety_validator_detects_drift", test_safety_validator_detects_drift, True),
        ("test_quarantine_and_restore_round_trip", test_quarantine_and_restore_round_trip, True),
        ("test_report_generator_schema_and_export", test_report_generator_schema_and_export, True),
    ]

    print("=" * 60)
    print("Running IADCS Comprehensive Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, func, takes_tmp in test_funcs:
        try:
            if takes_tmp:
                with tempfile.TemporaryDirectory() as td:
                    func(Path(td))
            else:
                func()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}")
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} PASSED, {failed} FAILED (Total: {len(test_funcs)})")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
