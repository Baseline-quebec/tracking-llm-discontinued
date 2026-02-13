"""BDD step definitions for registry update tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from src.deprecations import ModelLifecycle, load_registry, save_registry
from src.update_registry import update_registry


scenarios("features/update_registry.feature")


def _make_lifecycle(
    model: str,
    provider: str = "openai",
    replacement: str | None = "gpt-4.1",
) -> ModelLifecycle:
    return ModelLifecycle(
        model=model,
        provider=provider,
        status="retiring",
        shutdown_date=date(2026, 10, 1),
        replacement=replacement,
    )


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    return tmp_path / "registry.json"


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
def given_feed_with_new_model(
    model: str, provider: str, count: int
) -> list[ModelLifecycle]:
    return [_make_lifecycle(model, provider=provider.lower())]


@given(
    parsers.cfparse('a registry with model "{model}" replacement "{replacement}"'),
    target_fixture="seed_registry",
)
def given_registry_with_specific_model(
    registry_path: Path, model: str, replacement: str
) -> Path:
    models = {model: _make_lifecycle(model, replacement=replacement)}
    save_registry(models, registry_path)
    return registry_path


@given(
    parsers.cfparse('a feed returning model "{model}" with replacement "{replacement}"'),
    target_fixture="mock_feed",
)
def given_feed_with_replacement(model: str, replacement: str) -> list[ModelLifecycle]:
    return [_make_lifecycle(model, replacement=replacement)]


@given(
    "a feed returning no data",
    target_fixture="mock_feed",
)
def given_empty_feed() -> list[ModelLifecycle]:
    return []


# --- When steps ---


@when(
    "I run the registry update",
    target_fixture="update_result",
)
def run_update(
    registry_path: Path, mock_feed: list[ModelLifecycle]
) -> dict[str, int]:
    with (
        patch("src.update_registry.fetch_deprecations", return_value=mock_feed),
        patch("src.update_registry._create_feed_failure_issue"),
    ):
        feed_count = update_registry(registry_path)
    return {"feed_count": feed_count}


# --- Then steps ---


@then(parsers.cfparse("the registry should have {count:d} models"))
def check_registry_count(
    registry_path: Path, update_result: dict[str, int], count: int
) -> None:
    registry = load_registry(registry_path)
    assert len(registry) == count, (
        f"Expected {count} models, got {len(registry)}: {list(registry.keys())}"
    )


@then(parsers.cfparse('the registry should contain "{model}"'))
def check_registry_contains(
    registry_path: Path, update_result: dict[str, int], model: str
) -> None:
    registry = load_registry(registry_path)
    assert model in registry, f"Expected '{model}' in registry, got {list(registry.keys())}"


@then(parsers.cfparse('the registry entry "{model}" should have replacement "{replacement}"'))
def check_registry_replacement(
    registry_path: Path, update_result: dict[str, int], model: str, replacement: str
) -> None:
    registry = load_registry(registry_path)
    entry = registry.get(model)
    assert entry is not None, f"Model '{model}' not found in registry"
    assert entry.replacement == replacement, (
        f"Expected replacement '{replacement}', got '{entry.replacement}'"
    )
