"""BDD step definitions for registry update tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel, load_registry, save_registry
from src.update_registry import update_readme, update_registry


scenarios("features/update_registry.feature")


def _make_lifecycle(
    model: str,
    provider: str = "openai",
    status: str = "retiring",
) -> DeprecatedModel:
    return DeprecatedModel(
        model=model,
        provider=provider,
        status=status,
        shutdown_date=date(2026, 10, 1),
    )


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    return tmp_path / "registry.json"


@pytest.fixture
def readme_path(tmp_path: Path) -> Path:
    return tmp_path / "README.md"


# --- Given steps ---


@given(
    parsers.cfparse("a registry with {count:d} models"),
    target_fixture="seed_registry",
)
def given_registry_with_n_models(registry_path: Path, count: int) -> Path:
    models = {f"model-{i}": _make_lifecycle(f"model-{i}") for i in range(count)}
    save_registry(models, registry_path)
    return registry_path


@given(
    parsers.cfparse('a feed returning {count:d} new model "{model}" from "{provider}"'),
    target_fixture="mock_feed",
)
def given_feed_with_new_model(model: str, provider: str, count: int) -> list[DeprecatedModel]:
    return [_make_lifecycle(model, provider=provider.lower())]


@given(
    "a feed returning no data",
    target_fixture="mock_feed",
)
def given_empty_feed() -> list[DeprecatedModel]:
    return []


@given(
    parsers.cfparse('a registry with model "{model}" status "{status}"'),
    target_fixture="seed_registry",
)
def given_registry_with_specific_model(registry_path: Path, model: str, status: str) -> Path:
    models = {model: _make_lifecycle(model, status=status)}
    save_registry(models, registry_path)
    return registry_path


@given(
    parsers.cfparse('a feed returning model "{model}" with status "{status}"'),
    target_fixture="mock_feed",
)
def given_feed_with_status(model: str, status: str) -> list[DeprecatedModel]:
    return [_make_lifecycle(model, status=status)]


@given(
    "a README with registry markers",
    target_fixture="readme_with_markers",
)
def given_readme_with_markers(readme_path: Path) -> Path:
    content = (
        "# README\n\n<!-- REGISTRY_START -->\nOld table content\n<!-- REGISTRY_END -->\n\nFooter\n"
    )
    readme_path.write_text(content, encoding="utf-8")
    return readme_path


@given(
    "a README without registry markers",
    target_fixture="readme_without_markers",
)
def given_readme_without_markers(readme_path: Path) -> Path:
    content = "# README\n\nNo markers here.\n"
    readme_path.write_text(content, encoding="utf-8")
    return readme_path


@given("a README path that does not exist")
def given_readme_missing(readme_path: Path) -> None:
    """No-op: readme_path fixture returns a path with no file at it."""
    assert not readme_path.exists()


@given(
    parsers.cfparse('a feed with duplicate model "{model}"'),
    target_fixture="mock_feed",
)
def given_feed_with_duplicate(model: str) -> list[DeprecatedModel]:
    return [
        _make_lifecycle(model, status="retiring"),
        _make_lifecycle(model, status="shutdown"),
    ]


# --- When steps ---


@when(
    "I run the registry update",
    target_fixture="update_result",
)
def run_update(registry_path: Path, mock_feed: list[DeprecatedModel]) -> dict[str, object]:
    mock_issue = MagicMock()
    with (
        patch("src.update_registry.fetch_deprecations", return_value=mock_feed),
        patch("src.update_registry._create_feed_failure_issue", mock_issue),
    ):
        feed_count = update_registry(registry_path)
    return {"feed_count": feed_count, "mock_issue": mock_issue}


@when(
    "I call update_readme",
    target_fixture="readme_result",
)
def call_update_readme(
    registry_path: Path,
    readme_path: Path,
) -> bool:
    registry = load_registry(registry_path)
    return update_readme(registry, readme_path)


# --- Then steps ---


@then(parsers.cfparse("the registry should have {count:d} models"))
def check_registry_count(
    registry_path: Path, update_result: dict[str, object], count: int
) -> None:
    registry = load_registry(registry_path)
    assert len(registry) == count, (
        f"Expected {count} models, got {len(registry)}: {list(registry.keys())}"
    )


@then(parsers.cfparse('the registry should contain "{model}"'))
def check_registry_contains(
    registry_path: Path, update_result: dict[str, object], model: str
) -> None:
    registry = load_registry(registry_path)
    assert model in registry, f"Expected '{model}' in registry, got {list(registry.keys())}"


@then(parsers.cfparse('the registry should contain "{model}" with status "{status}"'))
def check_registry_model_status(
    registry_path: Path, update_result: dict[str, object], model: str, status: str
) -> None:
    registry = load_registry(registry_path)
    assert model in registry, f"Expected '{model}' in registry, got {list(registry.keys())}"
    assert registry[model].status == status, (
        f"Expected status '{status}', got '{registry[model].status}'"
    )


@then("the README should contain a registry table")
def check_readme_has_table(readme_path: Path, readme_result: bool) -> None:
    assert readme_result is True
    content = readme_path.read_text(encoding="utf-8")
    assert "| Model | Provider | Status | Shutdown date |" in content


@then("update_readme should return False")
def check_readme_false(readme_result: bool) -> None:
    assert readme_result is False


@then("_create_feed_failure_issue should have been called")
def check_feed_failure_issue_called(update_result: dict[str, object]) -> None:
    mock_issue: MagicMock = update_result["mock_issue"]
    mock_issue.assert_called_once()
