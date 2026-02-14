"""BDD step definitions for validate_patterns coverage tests."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from src.validate_patterns import validate_coverage


scenarios("features/validate_patterns.feature")


@given(
    "a temporary registry with the following models:",
    target_fixture="registry_path",
)
def given_temp_registry(tmp_path: Path, datatable: list[list[str]]) -> Path:
    headers = datatable[0]
    model_idx = headers.index("model")
    provider_idx = headers.index("provider")
    status_idx = headers.index("status")
    models = []
    for row in datatable[1:]:
        models.append(
            {
                "model": row[model_idx],
                "provider": row[provider_idx],
                "status": row[status_idx],
                "shutdown_date": None,
            }
        )
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(json.dumps({"models": models}, indent=2), encoding="utf-8")
    return registry_file


@when(
    "I validate pattern coverage",
    target_fixture="coverage_results",
)
def validate(registry_path: Path) -> dict[str, list[str]]:
    return validate_coverage(registry_path)


@then(
    parsers.cfparse("I should have {count:d} unmatched models"),
)
def check_unmatched_count(coverage_results: dict[str, list[str]], count: int) -> None:
    actual = len(coverage_results["unmatched"])
    assert actual == count, (
        f"Expected {count} unmatched, got {actual}: {coverage_results['unmatched']}"
    )


@then(
    parsers.cfparse('"{name}" should not appear in matched or unmatched'),
)
def check_not_in_results(coverage_results: dict[str, list[str]], name: str) -> None:
    all_models = coverage_results["matched"] + coverage_results["unmatched"]
    assert name not in all_models, (
        f"'{name}' should not appear in results but found in {all_models}"
    )
