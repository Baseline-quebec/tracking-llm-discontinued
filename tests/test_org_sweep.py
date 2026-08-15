"""BDD step definitions for the organisation-wide sweep."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.org_sweep import (
    Repository,
    SweepResult,
    build_summary,
    list_repositories,
    main,
    sweep_repository,
)


scenarios("features/org_sweep.feature")


def _gh_output(payload: list[dict[str, Any]], returncode: int = 0) -> MagicMock:
    """Mimic `gh api --jq`, which emits one JSON object per line."""
    process = MagicMock(spec=subprocess.CompletedProcess)
    process.returncode = returncode
    process.stdout = "\n".join(json.dumps(entry) for entry in payload)
    process.stderr = ""
    return process


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@given("the organisation lists an active repository and an archived repository")
def _active_and_archived(context: dict[str, Any]) -> None:
    # The installation endpoint returns archived repositories too, unlike
    # `gh repo list --no-archived`. Filtering is now ours to do, and forgetting
    # it would file issues on repositories nobody can act on.
    context["listing"] = _gh_output(
        [
            {"full_name": "org/active", "archived": False, "has_issues": True},
            {"full_name": "org/archive", "archived": True, "has_issues": True},
        ]
    )


@given("the organisation lists a repository with issues disabled")
def _issues_disabled(context: dict[str, Any]) -> None:
    context["listing"] = _gh_output(
        [{"full_name": "org/sans-issues", "archived": False, "has_issues": False}]
    )


@given(parsers.parse('the organisation lists repositories "{first}" and "{second}"'))
def _two_repositories(context: dict[str, Any], first: str, second: str) -> None:
    context["listing"] = _gh_output(
        [
            {"full_name": first, "archived": False, "has_issues": True},
            {"full_name": second, "archived": False, "has_issues": True},
        ]
    )


@given("the repository listing command fails")
def _listing_fails(context: dict[str, Any]) -> None:
    process = MagicMock(spec=subprocess.CompletedProcess)
    process.returncode = 1
    process.stdout = ""
    process.stderr = "HTTP 403"
    context["listing"] = process


@when("I list the repositories to sweep")
def _list_repositories(context: dict[str, Any]) -> None:
    with patch("src.gh.subprocess.run", return_value=context["listing"]):
        context["repositories"] = list_repositories("org")


@when(parsers.parse('I list the repositories excluding "{excluded}"'))
def _list_excluding(context: dict[str, Any], excluded: str) -> None:
    with patch("src.gh.subprocess.run", return_value=context["listing"]):
        context["repositories"] = list_repositories("org", {excluded})


@then("only the active repository should be listed")
def _only_active(context: dict[str, Any]) -> None:
    assert [r.name_with_owner for r in context["repositories"]] == ["org/active"]


@then("no repository should be listed")
def _none_listed(context: dict[str, Any]) -> None:
    assert context["repositories"] == []


@then(parsers.parse('only "{expected}" should be listed'))
def _only_expected(context: dict[str, Any], expected: str) -> None:
    assert [r.name_with_owner for r in context["repositories"]] == [expected]


def _clone_writing(content: str) -> Any:
    """Simulate gh repo clone by writing a file into the destination."""

    def _clone(repository: Repository, destination: Path) -> bool:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "config.py").write_text(content, encoding="utf-8")
        return True

    return _clone


@given("a repository referencing a deprecated model")
def _repository_with_deprecated(context: dict[str, Any]) -> None:
    context["clone"] = _clone_writing('MODEL = "claude-3-sonnet-20240229"\n')
    context["repository"] = Repository(name_with_owner="org/projet")


@given("a repository referencing only supported models")
def _repository_clean(context: dict[str, Any]) -> None:
    context["clone"] = _clone_writing("TIMEOUT = 30\n")
    context["repository"] = Repository(name_with_owner="org/propre")


@given("a repository that cannot be cloned")
def _repository_unclonable(context: dict[str, Any]) -> None:
    context["clone"] = lambda repository, destination: False
    context["repository"] = Repository(name_with_owner="org/prive")


@when("I sweep that repository")
def _sweep(context: dict[str, Any]) -> None:
    with (
        patch("src.org_sweep.clone", side_effect=context["clone"]),
        patch("src.org_sweep.create_issues", return_value=(1, 0)) as create_issues,
        patch("src.issue_reporter.check_deprecation") as check,
    ):
        check.side_effect = lambda model: (
            MagicMock(model=model) if "claude-3-sonnet" in model else None
        )
        context["result"] = sweep_repository(context["repository"], assignees=None, dry_run=False)
        context["create_issues"] = create_issues


@then("the issue should be created in that repository")
def _issue_targets_repository(context: dict[str, Any]) -> None:
    """The sweep scans clones, so gh must be told which repository to file in.

    Without an explicit target, gh infers the repository from the working
    directory and every alert lands in the sweeper's own repository.
    """
    _, kwargs = context["create_issues"].call_args
    assert kwargs["target_repo"] == "org/projet"


@then("one issue should be reported as created")
def _one_issue(context: dict[str, Any]) -> None:
    assert context["result"].issues_created == 1


@then("no issue should be created")
def _no_issue(context: dict[str, Any]) -> None:
    assert context["result"].issues_created == 0
    context["create_issues"].assert_not_called()


@then("the result should report a clone failure")
def _clone_failure(context: dict[str, Any]) -> None:
    assert context["result"].error == "clone failed"


@then("the repository should not be marked as scanned")
def _not_scanned(context: dict[str, Any]) -> None:
    assert context["result"].scanned is False


@then("the repository should be marked as scanned")
def _scanned(context: dict[str, Any]) -> None:
    assert context["result"].scanned is True


@given("sweep results with one affected repository and one failure")
def _mixed_results(context: dict[str, Any]) -> None:
    context["results"] = [
        SweepResult(
            repository="org/touche",
            scanned=True,
            deprecated_models=["claude-3-sonnet-20240229"],
            issues_created=1,
        ),
        SweepResult(repository="org/injoignable", scanned=False, error="clone failed"),
    ]


@given("sweep results with no affected repository")
def _clean_results(context: dict[str, Any]) -> None:
    context["results"] = [SweepResult(repository="org/propre", scanned=True)]


@when("I build the summary")
def _build(context: dict[str, Any]) -> None:
    context["summary"] = build_summary(context["results"])


@then("the summary should name the affected repository")
def _summary_names_affected(context: dict[str, Any]) -> None:
    assert "org/touche" in context["summary"]
    assert "claude-3-sonnet-20240229" in context["summary"]


@then("the summary should name the failed repository")
def _summary_names_failed(context: dict[str, Any]) -> None:
    assert "org/injoignable" in context["summary"]
    assert "clone failed" in context["summary"]


@given("no repository can be listed")
def _no_repository_listable(context: dict[str, Any]) -> None:
    """The usual cause is a token not authorised for the organisation.

    Under SAML single sign-on the GraphQL listing returns an empty array
    instead of an error, so the sweep would scan nothing and still succeed.
    """
    context["repositories"] = []


@when("I run the sweep")
def _run_main(context: dict[str, Any]) -> None:
    with patch("src.org_sweep.list_repositories", return_value=context["repositories"]):
        context["exit_code"] = main(["--org", "org"])


@then("the run should fail")
def _run_failed(context: dict[str, Any]) -> None:
    assert context["exit_code"] == 1


@then("the summary should state that no deprecated model was found")
def _summary_clean(context: dict[str, Any]) -> None:
    assert "Aucun modèle déprécié" in context["summary"]
