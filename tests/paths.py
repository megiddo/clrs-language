"""Shared paths for tests that read the nine-file contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SORTING = ROOT / "lib" / "sorting"
FIXTURES = ROOT / "tests" / "fixtures"
