"""Duplicate detection and verification module for IADCS."""
from app.duplicate.candidate_matcher import CandidateMatcher
from app.duplicate.duplicate_detector import DuplicateDetector
from app.duplicate.verifier import verify_applications_byte_by_byte, verify_files_byte_by_byte

__all__ = [
    "CandidateMatcher",
    "DuplicateDetector",
    "verify_applications_byte_by_byte",
    "verify_files_byte_by_byte",
]
