"""BDD step definitions for repository scanner tests."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when
from src.models import ScanResult
from src.scanner import scan_directory


scenarios("features/scanner.feature")


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


@then(
    parsers.cfparse("I should find at least {count:d} scan matches"),
)
def check_scan_match_at_least(scan_result: ScanResult, count: int) -> None:
    assert scan_result.match_count >= count, (
        f"Expected at least {count} matches, got {scan_result.match_count}: {scan_result.matches}"
    )


