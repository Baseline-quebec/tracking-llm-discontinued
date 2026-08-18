"""BDD step definitions for main CLI module tests.

Les scenarios de bout en bout s'executent contre `tests/data/registry_fige.json`
et non contre `data/registry.json`. Ils affirment qu'un modele est deprecie et
qu'un autre ne l'est pas ; or le vrai registre est reecrit tous les quinze jours
depuis deprecations.info. « `gpt-4.1` n'est pas signale » est vrai aujourd'hui et
faux le jour ou OpenAI annonce son retrait, sans qu'une ligne de code ait bouge.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel
from src.issue_reporter import DeprecationAlert, alerts_from_matches
from src.main import _build_deprecated_summary, _set_github_output, parse_args
from src.models import ScanMatch
from src.scanner import scan_directory


scenarios("features/main.feature")

pytestmark = pytest.mark.usefixtures("registre_fige")


def _make_match(model: str, match_type: str = "llm") -> ScanMatch:
    return ScanMatch(
        provider="openai",
        model=model,
        match_type=match_type,
        file="config.py",
        line=1,
    )


# --- Given steps ---


@given(
    parsers.cfparse('CLI arguments "{args_str}"'),
    target_fixture="cli_args",
)
def given_cli_args(args_str: str) -> list[str]:
    return args_str.split()


@given(
    parsers.cfparse('scan matches with models "{models}"'),
    target_fixture="scan_matches",
)
def given_scan_matches(models: str) -> list[ScanMatch]:
    matches = []
    for m in models.split(","):
        model = m.strip()
        mtype = "embedding" if "embedding" in model else "llm"
        matches.append(_make_match(model, match_type=mtype))
    return matches


@given(
    parsers.cfparse('deprecation alerts for "{model}" appearing {count:d} times'),
    target_fixture="dup_alerts",
)
def given_duplicate_alerts(model: str, count: int) -> list[DeprecationAlert]:
    lifecycle = DeprecatedModel(
        model=model,
        provider="openai",
        status="retiring",
        shutdown_date=date(2026, 10, 1),
    )
    return [
        DeprecationAlert(
            match=ScanMatch(
                provider="openai",
                model=model,
                match_type="llm",
                file=f"file{i}.py",
                line=i + 1,
            ),
            lifecycle=lifecycle,
        )
        for i in range(count)
    ]


@given(
    "a temporary GITHUB_OUTPUT file",
    target_fixture="github_output_path",
)
def given_github_output(tmp_path: Path) -> Path:
    output_file = tmp_path / "github_output"
    output_file.touch()
    return output_file


# --- When steps ---


@when(
    "I parse the arguments",
    target_fixture="parsed_args",
)
def parse_arguments(cli_args: list[str]) -> dict[str, str | bool]:
    args = parse_args(cli_args)
    return {
        "repo_name": args.repo_name,
        "scan_path": args.scan_path,
        "assignees": args.assignees,
        "dry_run": args.dry_run,
    }


@when(
    "I check for deprecated models",
    target_fixture="deprecated_alerts",
)
def check_deprecated(scan_matches: list[ScanMatch]) -> list[DeprecationAlert]:
    return alerts_from_matches(scan_matches)


@when(
    "I build the deprecated summary",
    target_fixture="summary",
)
def build_summary(dup_alerts: list[DeprecationAlert]) -> list[dict[str, str]]:
    return _build_deprecated_summary(dup_alerts)


@when(
    parsers.cfparse('I set output "{name}" to "{value}"'),
    target_fixture="output_written",
)
def set_output(github_output_path: Path, name: str, value: str) -> Path:
    import os

    with patch.dict(os.environ, {"GITHUB_OUTPUT": str(github_output_path)}):
        _set_github_output(name, value)
    return github_output_path


@when(
    parsers.cfparse('I run main in dry-run for repo "{repo_name}"'),
    target_fixture="main_result",
)
def run_main_dry(scan_dir: Path, repo_name: str) -> dict[str, int]:
    from src.main import main

    with patch("src.gh.subprocess.run"):
        try:
            main(["--repo-name", repo_name, "--scan-path", str(scan_dir), "--dry-run"])
            return {"exit_code": 0}
        except SystemExit as exc:
            return {"exit_code": exc.code or 0}


# --- Then steps ---


@then(parsers.cfparse('repo_name should be "{expected}"'))
def check_repo_name(parsed_args: dict[str, str | bool], expected: str) -> None:
    assert parsed_args["repo_name"] == expected


@then(parsers.cfparse('scan_path should be "{expected}"'))
def check_scan_path(parsed_args: dict[str, str | bool], expected: str) -> None:
    assert parsed_args["scan_path"] == expected


@then(parsers.cfparse('assignees should be "{expected}"'))
def check_assignees(parsed_args: dict[str, str | bool], expected: str) -> None:
    assert parsed_args["assignees"] == expected


@then(parsers.cfparse("dry_run should be {expected}"))
def check_dry_run(parsed_args: dict[str, str | bool], expected: str) -> None:
    assert parsed_args["dry_run"] == (expected == "true")


@then(parsers.cfparse("I should find {count:d} deprecated alerts"))
def check_deprecated_count(deprecated_alerts: list[DeprecationAlert], count: int) -> None:
    assert len(deprecated_alerts) == count, (
        f"Expected {count}, got {len(deprecated_alerts)}: "
        f"{[a.lifecycle.model for a in deprecated_alerts]}"
    )


@then(parsers.cfparse('the deprecated models should include "{model}"'))
def check_deprecated_includes(deprecated_alerts: list[DeprecationAlert], model: str) -> None:
    models = [a.lifecycle.model for a in deprecated_alerts]
    assert model in models, f"Expected '{model}' in {models}"


@then(parsers.cfparse("the summary should have {count:d} entries"))
def check_summary_count(summary: list[dict[str, str]], count: int) -> None:
    assert len(summary) == count, f"Expected {count} entries, got {len(summary)}"


@then(parsers.cfparse('the output file should contain "{text}"'))
def check_output_file(output_written: Path, text: str) -> None:
    content = output_written.read_text()
    assert text in content, f"Expected '{text}' in output file content: {content}"


@then(parsers.cfparse("the exit code should be {code:d}"))
def check_exit_code(main_result: dict[str, int], code: int) -> None:
    assert main_result["exit_code"] == code


# --- Steps for broad end-to-end tests ---


@when(
    parsers.cfparse('I scan and check deprecations for repo "{repo_name}"'),
    target_fixture="e2e_result",
)
def scan_and_check_deprecations(
    scan_dir: Path, repo_name: str
) -> dict[str, list[DeprecationAlert] | list[ScanMatch]]:
    result = scan_directory(scan_dir, repo_name)
    alerts = alerts_from_matches(result.matches)
    return {"alerts": alerts, "matches": result.matches}


@then(parsers.cfparse("I should find at least {count:d} deprecated references"))
def check_at_least_deprecated(
    e2e_result: dict[str, list[DeprecationAlert] | list[ScanMatch]], count: int
) -> None:
    alerts: list[DeprecationAlert] = e2e_result["alerts"]  # type: ignore[assignment]
    assert len(alerts) >= count, (
        f"Expected at least {count} deprecated, got {len(alerts)}: "
        f"{[a.lifecycle.model for a in alerts]}"
    )


@then(parsers.cfparse("I should find {count:d} deprecated references"))
def check_exact_deprecated(
    e2e_result: dict[str, list[DeprecationAlert] | list[ScanMatch]], count: int
) -> None:
    alerts: list[DeprecationAlert] = e2e_result["alerts"]  # type: ignore[assignment]
    assert len(alerts) == count, (
        f"Expected {count} deprecated, got {len(alerts)}: {[a.lifecycle.model for a in alerts]}"
    )


@then(parsers.cfparse('deprecated models should include "{model}"'))
def check_e2e_deprecated_includes(
    e2e_result: dict[str, list[DeprecationAlert] | list[ScanMatch]], model: str
) -> None:
    alerts: list[DeprecationAlert] = e2e_result["alerts"]  # type: ignore[assignment]
    models = [a.lifecycle.model for a in alerts]
    assert model in models, f"Expected '{model}' in deprecated models {models}"


@then(parsers.cfparse('deprecated models should not include "{model}"'))
def check_e2e_deprecated_excludes(
    e2e_result: dict[str, list[DeprecationAlert] | list[ScanMatch]], model: str
) -> None:
    alerts: list[DeprecationAlert] = e2e_result["alerts"]  # type: ignore[assignment]
    models = [a.lifecycle.model for a in alerts]
    assert model not in models, f"'{model}' should not be reported, got {models}"


@then(parsers.cfparse('active models should not be flagged: "{models_str}"'))
def check_active_not_flagged(
    e2e_result: dict[str, list[DeprecationAlert] | list[ScanMatch]], models_str: str
) -> None:
    alerts: list[DeprecationAlert] = e2e_result["alerts"]  # type: ignore[assignment]
    deprecated_models = {a.lifecycle.model for a in alerts}
    for model in models_str.split(","):
        model = model.strip()
        assert model not in deprecated_models, (
            f"Active model '{model}' should not be flagged as deprecated"
        )
