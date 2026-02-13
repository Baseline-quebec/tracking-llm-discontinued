"""Shared BDD step definitions and fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given


@pytest.fixture
def tmp_scan_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for scanning."""
    return tmp_path


@given(
    "a temporary directory with the following files:",
    target_fixture="scan_dir",
)
def given_temp_dir_with_files(
    tmp_scan_dir: Path,
    datatable: list[list[str]],
) -> Path:
    """Create files from a datatable in a temporary directory."""
    headers = datatable[0]
    path_idx = headers.index("path")
    content_idx = headers.index("content")
    for row in datatable[1:]:
        file_path = tmp_scan_dir / row[path_idx]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = row[content_idx].replace("\\n", "\n")
        file_path.write_text(content, encoding="utf-8")
    return tmp_scan_dir


@given(
    "an empty temporary directory",
    target_fixture="scan_dir",
)
def given_empty_dir(tmp_scan_dir: Path) -> Path:
    return tmp_scan_dir
