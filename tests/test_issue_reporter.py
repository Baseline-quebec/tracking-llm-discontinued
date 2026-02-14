"""BDD step definitions for issue reporter tests."""

from __future__ import annotations

import subprocess
from datetime import date
from unittest.mock import patch

from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel
from src.issue_reporter import (
    DeprecationAlert,
    _build_body,
    _build_title,
    _validate_assignees,
    create_issues,
)
from src.models import ScanMatch


scenarios("features/issue_reporter.feature")


def _make_lifecycle(
    model: str,
    status: str = "retiring",
    provider: str = "openai",
) -> DeprecatedModel:
    return DeprecatedModel(
        model=model,
        provider=provider,
        status=status,
        shutdown_date=date(2026, 10, 1),
    )


def _make_alert(
    model: str,
    file: str = "config.py",
    line: int = 1,
    status: str = "retiring",
) -> DeprecationAlert:
    return DeprecationAlert(
        match=ScanMatch(
            provider="openai",
            model=model,
            match_type="llm",
            file=file,
            line=line,
        ),
        lifecycle=_make_lifecycle(model, status=status),
    )


# --- Given steps ---


@given(
    parsers.cfparse('a model lifecycle for "{model}" with status "{status}"'),
    target_fixture="lifecycle",
)
def given_lifecycle(model: str, status: str) -> DeprecatedModel:
    return _make_lifecycle(model, status=status)


@given(
    parsers.cfparse('a deprecation alert for "{model}" in file "{file}" at line {line:d}'),
    target_fixture="alert",
)
def given_alert(model: str, file: str, line: int) -> DeprecationAlert:
    return _make_alert(model, file=file, line=line)


@given(
    parsers.cfparse('a list of deprecation alerts for models "{models}"'),
    target_fixture="alerts",
)
def given_alerts_for_models(models: str) -> list[DeprecationAlert]:
    return [_make_alert(m.strip()) for m in models.split(",")]


@given(
    parsers.cfparse('a list of deprecation alerts with "{model}" in {count:d} different files'),
    target_fixture="alerts",
)
def given_alerts_multiple_files(model: str, count: int) -> list[DeprecationAlert]:
    return [_make_alert(model, file=f"src/file{i}.py", line=i + 1) for i in range(count)]


@given(
    "an empty list of deprecation alerts",
    target_fixture="alerts",
)
def given_empty_alerts() -> list[DeprecationAlert]:
    return []


@given(
    parsers.cfparse('assignees "{assignees_str}"'),
    target_fixture="raw_assignees",
)
def given_assignees(assignees_str: str) -> list[str]:
    return [a.strip() for a in assignees_str.split(",")]


# --- When steps ---


@when(
    "I build the issue title",
    target_fixture="title",
)
def build_title(lifecycle: DeprecatedModel) -> str:
    return _build_title(lifecycle)


@when(
    "I build the issue body",
    target_fixture="body",
)
def build_body(alert: DeprecationAlert) -> str:
    return _build_body(alert.lifecycle, [alert])


@when(
    "I create issues in dry-run mode",
    target_fixture="create_result",
)
def create_issues_dry_run(alerts: list[DeprecationAlert]) -> dict[str, int | bool]:
    with patch("src.issue_reporter.subprocess.run") as mock_run:
        count = create_issues(alerts, dry_run=True)
        return {"count": count, "subprocess_called": mock_run.called}


@when(
    "I create issues with gh CLI failing",
    target_fixture="create_result",
)
def create_issues_gh_failure(alerts: list[DeprecationAlert]) -> dict[str, int | bool]:
    mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("src.issue_reporter.subprocess.run", return_value=mock_result):
        count = create_issues(alerts, dry_run=False)
        return {"count": count, "subprocess_called": True}


@when(
    "I validate the assignees",
    target_fixture="validated_assignees",
)
def validate_assignees(raw_assignees: list[str]) -> list[str] | None:
    return _validate_assignees(raw_assignees)


# --- Then steps ---


@then(
    parsers.cfparse('the title should contain "{text}"'),
)
def check_title_contains(title: str, text: str) -> None:
    assert text in title, f"Expected '{text}' in title '{title}'"


@then(
    parsers.cfparse('the title should start with "{prefix}"'),
)
def check_title_starts(title: str, prefix: str) -> None:
    assert title.startswith(prefix), f"Expected title to start with '{prefix}', got '{title}'"


@then(
    parsers.cfparse('the body should contain "{text}"'),
)
def check_body_contains(body: str, text: str) -> None:
    assert text in body, f"Expected '{text}' in body"


@then(
    parsers.cfparse("{count:d} issues should be reported as created"),
)
def check_issues_created(create_result: dict[str, int | bool], count: int) -> None:
    assert create_result["count"] == count, (
        f"Expected {count} issues created, got {create_result['count']}"
    )


@then(
    "gh CLI should not have been called",
)
def check_no_subprocess(create_result: dict[str, int | bool]) -> None:
    assert not create_result["subprocess_called"], (
        "subprocess.run should not have been called in dry-run"
    )


@then(
    parsers.cfparse('valid assignees should be "{expected}"'),
)
def check_valid_assignees(validated_assignees: list[str] | None, expected: str) -> None:
    expected_list = [a.strip() for a in expected.split(",")]
    assert validated_assignees == expected_list, (
        f"Expected {expected_list}, got {validated_assignees}"
    )
