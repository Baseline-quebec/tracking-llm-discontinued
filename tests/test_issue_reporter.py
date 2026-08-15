"""BDD step definitions for issue reporter tests."""

from __future__ import annotations

import subprocess
from datetime import date
from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel
from src.issue_reporter import (
    DeprecationAlert,
    _build_body,
    _build_title,
    _issue_exists,
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
    return _build_title(lifecycle.model)


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
    with patch("src.gh.subprocess.run") as mock_run:
        count, _failed = create_issues(alerts, dry_run=True)
        commands = [" ".join(call.args[0]) for call in mock_run.call_args_list]
        return {
            "count": count,
            "subprocess_called": mock_run.called,
            "wrote": any("issue create" in c or "label create" in c for c in commands),
        }


@when(
    "I create issues with gh CLI failing",
    target_fixture="create_result",
)
def create_issues_gh_failure(alerts: list[DeprecationAlert]) -> dict[str, int | bool]:
    mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("src.gh.subprocess.run", return_value=mock_result):
        count, _failed = create_issues(alerts, dry_run=False)
        return {"count": count, "subprocess_called": True}


@when(
    "I create issues with gh CLI timing out",
    target_fixture="create_result",
)
def create_issues_gh_timeout(alerts: list[DeprecationAlert]) -> dict[str, int | bool]:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["gh"], timeout=30)

    with patch("src.gh.subprocess.run", side_effect=raise_timeout):
        count, _failed = create_issues(alerts, dry_run=False)
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
    "gh CLI should not have been called to write",
)
def check_no_write(create_result: dict[str, int | bool]) -> None:
    """Dry-run must not write, but it may read.

    The deduplication check runs in dry-run on purpose: without it the
    rehearsal counted every alert as new and overestimated what a real run
    would file, which defeats the point of rehearsing.
    """
    assert not create_result["wrote"], "no issue or label should be created in dry-run"


@then(
    parsers.cfparse('valid assignees should be "{expected}"'),
)
def check_valid_assignees(validated_assignees: list[str] | None, expected: str) -> None:
    expected_list = [a.strip() for a in expected.split(",")]
    assert validated_assignees == expected_list, (
        f"Expected {expected_list}, got {validated_assignees}"
    )


# --- Webhook integration steps ---


def _gh_success(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Simulate gh CLI returning an issue URL."""
    cmd = args[0] if args else kwargs.get("args", [])
    if isinstance(cmd, list) and "create" in cmd:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/org/repo/issues/42\n",
            stderr="",
        )
    # label create / issue list: succeed with empty result
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="[]", stderr="")


@when(
    "I create issues with webhook enabled",
    target_fixture="create_result",
)
def create_issues_with_webhook(alerts: list[DeprecationAlert]) -> dict[str, object]:
    webhook_mock = MagicMock(return_value=True)
    with (
        patch("src.gh.subprocess.run", side_effect=_gh_success),
        patch("src.issue_reporter.send_webhook", webhook_mock),
    ):
        count, _failed = create_issues(
            alerts,
            dry_run=False,
            webhook_url="https://example.com/webhook",
            repo_name="org/repo",
        )
    return {"count": count, "subprocess_called": True, "webhook_mock": webhook_mock}


@when(
    "I create issues with webhook failing",
    target_fixture="create_result",
)
def create_issues_with_webhook_failing(alerts: list[DeprecationAlert]) -> dict[str, object]:
    webhook_mock = MagicMock(return_value=False)
    with (
        patch("src.gh.subprocess.run", side_effect=_gh_success),
        patch("src.issue_reporter.send_webhook", webhook_mock),
    ):
        count, _failed = create_issues(
            alerts,
            dry_run=False,
            webhook_url="https://example.com/webhook",
            repo_name="org/repo",
        )
    return {"count": count, "subprocess_called": True, "webhook_mock": webhook_mock}


@then(
    parsers.cfparse("webhook should have been called {count:d} time"),
)
def check_webhook_called(create_result: dict[str, object], count: int) -> None:
    webhook_mock: MagicMock = create_result["webhook_mock"]  # type: ignore[assignment]
    assert webhook_mock.call_count == count, (
        f"Expected webhook called {count} time(s), got {webhook_mock.call_count}"
    )


# --- Unit tests for _issue_exists (regression for substring false-positive bug) ---


def _gh_list_issues(titles: list[str]) -> subprocess.CompletedProcess[str]:
    """Build a gh CLI 'issue list --json' response with the given titles."""
    payload = [{"number": i + 1, "title": t} for i, t in enumerate(titles)]
    import json as _json

    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=_json.dumps(payload), stderr=""
    )


def test_issue_exists_returns_true_on_exact_title_match() -> None:
    """When an open issue exactly matches the model title, _issue_exists is True."""
    fake = _gh_list_issues(["Modèle déprécié : gpt-4"])
    with patch("src.gh.subprocess.run", return_value=fake):
        assert _issue_exists("gpt-4") is True


def test_issue_exists_returns_false_when_only_superstring_match() -> None:
    """A title for 'gpt-4o' must NOT count as an existing issue for 'gpt-4'.

    Regression: previously the check used substring matching, which falsely
    blocked creating issues for 'gpt-4' when an open 'gpt-4o' issue existed.
    """
    fake = _gh_list_issues(["Modèle déprécié : gpt-4o"])
    with patch("src.gh.subprocess.run", return_value=fake):
        assert _issue_exists("gpt-4") is False


def test_issue_exists_returns_false_when_title_is_substring() -> None:
    """A 'gpt-4o-mini' lookup must NOT match a 'gpt-4o' open issue."""
    fake = _gh_list_issues(["Modèle déprécié : gpt-4o"])
    with patch("src.gh.subprocess.run", return_value=fake):
        assert _issue_exists("gpt-4o-mini") is False


def test_issue_exists_returns_false_for_unsafe_model_name() -> None:
    """Model names with unsafe chars are rejected without calling gh."""
    with patch("src.gh.subprocess.run") as mock_run:
        assert _issue_exists("gpt-4; rm -rf /") is False
        mock_run.assert_not_called()


def test_issue_exists_returns_false_on_gh_failure() -> None:
    """When gh CLI returns non-zero, treat as 'no existing issue' (proceed)."""
    fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="auth failed")
    with patch("src.gh.subprocess.run", return_value=fail):
        assert _issue_exists("gpt-4") is False


def test_issue_exists_returns_false_on_invalid_json() -> None:
    """Malformed gh CLI output is handled without raising."""
    bad = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
    with patch("src.gh.subprocess.run", return_value=bad):
        assert _issue_exists("gpt-4") is False


def test_issue_exists_returns_false_on_timeout() -> None:
    """Gh CLI timeout is handled and returns False (proceed with creation)."""

    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["gh"], timeout=30)

    with patch("src.gh.subprocess.run", side_effect=raise_timeout):
        assert _issue_exists("gpt-4") is False
