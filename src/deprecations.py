"""Registry of deprecated/retiring LLM models with lifecycle data.

Source: https://deprecations.info/
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal


logger = logging.getLogger(__name__)

_DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "registry.json"

DeprecationStatus = Literal["retiring", "deprecated", "shutdown"]

# Matches date suffixes like -20240229, -2024-08-06, -20241022
_DATE_SUFFIX_RE = re.compile(r"-\d{4}-?\d{2}-?\d{2}$")


@dataclass(frozen=True)
class DeprecatedModel:
    """Information about a deprecated or retiring model."""

    model: str
    provider: str
    status: DeprecationStatus
    shutdown_date: date | None = None


_VALID_PROVIDERS = {"openai", "anthropic", "google"}
_VALID_STATUSES = {"retiring", "deprecated", "shutdown"}


def _validate_entry(entry: dict[str, Any]) -> bool:
    """Validate that a registry entry has the required fields and valid values."""
    model = entry.get("model")
    if not isinstance(model, str) or not model:
        return False

    provider = entry.get("provider")
    if provider not in _VALID_PROVIDERS:
        return False

    status = entry.get("status")
    if status not in _VALID_STATUSES:
        return False

    shutdown_str = entry.get("shutdown_date")
    if shutdown_str is not None:
        try:
            date.fromisoformat(shutdown_str)
        except (ValueError, TypeError):
            return False

    return True


def _entry_to_deprecated(entry: dict[str, Any]) -> DeprecatedModel:
    """Convert a JSON entry to a DeprecatedModel object."""
    shutdown_str = entry.get("shutdown_date")
    return DeprecatedModel(
        model=entry["model"],
        provider=entry["provider"],
        status=entry["status"],
        shutdown_date=date.fromisoformat(shutdown_str) if shutdown_str else None,
    )


def _deprecated_to_dict(dm: DeprecatedModel) -> dict[str, Any]:
    """Convert a DeprecatedModel object to a JSON-serializable dict."""
    return {
        "model": dm.model,
        "provider": dm.provider,
        "status": dm.status,
        "shutdown_date": dm.shutdown_date.isoformat() if dm.shutdown_date else None,
    }


def load_registry(path: Path | None = None) -> dict[str, DeprecatedModel]:
    """Load registry from JSON file.

    Args:
        path: Path to the registry JSON file. Defaults to data/registry.json.

    Returns:
        Dictionary mapping model names to DeprecatedModel objects.
    """
    registry_path = path or _DEFAULT_REGISTRY_PATH
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load registry from %s: %s", registry_path, exc)
        return {}
    registry: dict[str, DeprecatedModel] = {}
    for entry in data.get("models", []):
        if not _validate_entry(entry):
            logger.warning("Skipping invalid registry entry: %s", entry)
            continue
        dm = _entry_to_deprecated(entry)
        registry[dm.model.lower()] = dm
    return registry


def save_registry(registry: dict[str, DeprecatedModel], path: Path) -> None:
    """Save registry to JSON file.

    Sorts entries by (provider, model) for clean diffs.

    Args:
        registry: Dictionary mapping model names to DeprecatedModel objects.
        path: Path to write the registry JSON file.
    """
    sorted_entries = sorted(registry.values(), key=lambda dm: (dm.provider, dm.model))
    data = {
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "models": [_deprecated_to_dict(dm) for dm in sorted_entries],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def merge_registries(
    static: dict[str, DeprecatedModel],
    feed: list[DeprecatedModel],
) -> dict[str, DeprecatedModel]:
    """Merge static registry with live feed data.

    Feed entries take priority over static entries for the same model.
    Keys are stored in lowercase for case-insensitive lookup.
    """
    merged = dict(static)
    for entry in feed:
        merged[entry.model.lower()] = entry
    return merged


DEPRECATION_REGISTRY: dict[str, DeprecatedModel] = load_registry()


def check_deprecation(model: str) -> DeprecatedModel | None:
    """Look up deprecation info for a model.

    Handles date-suffixed model names (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
    by stripping the suffix and retrying the lookup.

    Returns DeprecatedModel if the model is deprecated/retiring, None otherwise.
    """
    model_lower = model.lower()
    result = DEPRECATION_REGISTRY.get(model_lower)
    if result is not None:
        return result

    # Try stripping date suffix (e.g. "claude-3.5-sonnet-20241022" -> "claude-3.5-sonnet")
    base = _DATE_SUFFIX_RE.sub("", model_lower)
    if base != model_lower:
        return DEPRECATION_REGISTRY.get(base)

    return None
