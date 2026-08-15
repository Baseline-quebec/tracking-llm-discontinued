"""BDD step definitions for model deprecation detection tests.

Ces scenarios s'executent contre `tests/data/registry_fige.json` et non contre
`data/registry.json`. Le vrai registre est reecrit tous les quinze jours par le
workflow de mise a jour : y coder en dur qu'un modele est `deprecated` faisait
echouer la suite des que deprecations.info changeait son statut, ce qui n'apprend
rien sur `check_deprecation`. Le registre fige teste la mecanique (les trois
statuts, le retrait du suffixe de date, l'absence du registre) sur des donnees
qui, elles, ne bougent pas.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel, check_deprecation
from src.issue_reporter import DeprecationAlert
from src.scanner import scan_directory


scenarios("features/deprecations.feature")

pytestmark = pytest.mark.usefixtures("registre_fige")


@given(
    parsers.cfparse('a model name "{model}"'),
    target_fixture="model_name",
)
def given_model_name(model: str) -> str:
    return model


@when(
    "I check its deprecation status",
    target_fixture="deprecation_result",
)
def check_deprecation_status(model_name: str) -> DeprecatedModel | None:
    return check_deprecation(model_name)


@when(
    parsers.cfparse('I scan and check deprecations for repo "{repo_name}"'),
    target_fixture="deprecation_alerts",
)
def scan_and_check_deprecations(scan_dir: Path, repo_name: str) -> list[DeprecationAlert]:
    result = scan_directory(scan_dir, repo_name)
    alerts: list[DeprecationAlert] = []
    for match in result.matches:
        lifecycle = check_deprecation(match.model)
        if lifecycle is not None:
            alerts.append(DeprecationAlert(match=match, lifecycle=lifecycle))
    return alerts


@then(
    parsers.cfparse('the model should be "{status}"'),
)
def check_status(deprecation_result: DeprecatedModel | None, status: str) -> None:
    assert deprecation_result is not None, "Expected model to be in deprecation registry"
    assert deprecation_result.status == status, (
        f"Expected status '{status}', got '{deprecation_result.status}'"
    )


@then(
    "the model should not be deprecated",
)
def check_not_deprecated(deprecation_result: DeprecatedModel | None) -> None:
    assert deprecation_result is None, (
        f"Expected model to NOT be in deprecation registry, got {deprecation_result}"
    )


@then(
    parsers.cfparse("I should find {count:d} deprecation alerts"),
)
def check_alert_count(deprecation_alerts: list[DeprecationAlert], count: int) -> None:
    assert len(deprecation_alerts) == count, (
        f"Expected {count} alerts, got {len(deprecation_alerts)}: "
        f"{[a.lifecycle.model for a in deprecation_alerts]}"
    )


@then(
    parsers.cfparse('the alerts should include model "{model}" with status "{status}"'),
)
def check_alert_model_status(
    deprecation_alerts: list[DeprecationAlert],
    model: str,
    status: str,
) -> None:
    found = [(a.lifecycle.model, a.lifecycle.status) for a in deprecation_alerts]
    assert (model, status) in found, f"Expected ({model}, {status}) in {found}"
