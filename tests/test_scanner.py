"""BDD step definitions for repository scanner tests."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from src.models import ScanResult
from src.scanner import MAX_FILE_SIZE, scan_directory


scenarios("features/scanner.feature")


@given(
    parsers.cfparse('a temporary directory with a large file "{filename}" containing "{content}"'),
    target_fixture="scan_dir",
)
def given_large_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Create a file larger than MAX_FILE_SIZE in a temporary directory."""
    file_path = tmp_path / filename
    # Write content padded to exceed MAX_FILE_SIZE
    padding = "x" * (MAX_FILE_SIZE + 1 - len(content))
    file_path.write_text(f'model = "{content}"\n{padding}', encoding="utf-8")
    return tmp_path


@given(
    "a non-existent scan path",
    target_fixture="scan_dir",
)
def given_nonexistent_path(tmp_path: Path) -> Path:
    return tmp_path / "does_not_exist"


@when(
    parsers.cfparse('I scan the directory for repo "{repo_name}"'),
    target_fixture="scan_result",
)
def scan_dir(scan_dir: Path, repo_name: str) -> ScanResult:
    return scan_directory(scan_dir, repo_name)


@then(
    parsers.cfparse("I should find {count:d} scan matches"),
)
def check_scan_match_count(scan_result: ScanResult, count: int) -> None:
    assert scan_result.match_count == count, (
        f"Expected {count} matches, got {scan_result.match_count}: {scan_result.matches}"
    )


@then(
    parsers.cfparse('the results should contain model "{model}"'),
)
def check_result_contains_model(scan_result: ScanResult, model: str) -> None:
    models = [m.model for m in scan_result.matches]
    assert model in models, f"Expected model '{model}' in {models}"
