"""Registry of deprecated/retiring LLM models with lifecycle data.

Sources:
    OpenAI: https://platform.openai.com/docs/deprecations
    Anthropic: https://platform.claude.com/docs/en/about-claude/model-deprecations
    Google: https://ai.google.dev/gemini-api/docs/deprecations
    deprecations.info: https://deprecations.info/
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
class ModelLifecycle:
    """Lifecycle information for a deprecated or retiring model."""

    model: str
    provider: str
    status: DeprecationStatus
    shutdown_date: date | None = None
    replacement: str | None = None
    note: str = ""


def _entry_to_lifecycle(entry: dict[str, Any]) -> ModelLifecycle:
    """Convert a JSON entry to a ModelLifecycle object."""
    shutdown_str = entry.get("shutdown_date")
    return ModelLifecycle(
        model=entry["model"],
        provider=entry["provider"],
        status=entry["status"],
        shutdown_date=date.fromisoformat(shutdown_str) if shutdown_str else None,
        replacement=entry.get("replacement"),
        note=entry.get("note", ""),
    )


def _lifecycle_to_dict(lc: ModelLifecycle) -> dict[str, Any]:
    """Convert a ModelLifecycle object to a JSON-serializable dict."""
    return {
        "model": lc.model,
        "provider": lc.provider,
        "status": lc.status,
        "shutdown_date": lc.shutdown_date.isoformat() if lc.shutdown_date else None,
        "replacement": lc.replacement,
        "note": lc.note,
    }


def load_registry(path: Path | None = None) -> dict[str, ModelLifecycle]:
    """Load registry from JSON file.

    Args:
        path: Path to the registry JSON file. Defaults to data/registry.json.

    Returns:
        Dictionary mapping model names to ModelLifecycle objects.
    """
    registry_path = path or _DEFAULT_REGISTRY_PATH
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load registry from %s: %s", registry_path, exc)
        return {}
    registry: dict[str, ModelLifecycle] = {}
    for entry in data.get("models", []):
        lc = _entry_to_lifecycle(entry)
        registry[lc.model] = lc
    return registry


def save_registry(registry: dict[str, ModelLifecycle], path: Path) -> None:
    """Save registry to JSON file.

    Sorts entries by (provider, model) for clean diffs.

    Args:
        registry: Dictionary mapping model names to ModelLifecycle objects.
        path: Path to write the registry JSON file.
    """
    sorted_entries = sorted(registry.values(), key=lambda lc: (lc.provider, lc.model))
    data = {
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "models": [_lifecycle_to_dict(lc) for lc in sorted_entries],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def merge_registries(
    static: dict[str, ModelLifecycle],
    feed: list[ModelLifecycle],
) -> dict[str, ModelLifecycle]:
    """Merge static registry with live feed data.

    Feed entries take priority over static entries for the same model.
    """
    merged = dict(static)
    for entry in feed:
        merged[entry.model] = entry
    return merged


DEPRECATION_REGISTRY: dict[str, ModelLifecycle] = load_registry()


def check_deprecation(model: str) -> ModelLifecycle | None:
    """Look up deprecation info for a model.

    Handles date-suffixed model names (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
    by stripping the suffix and retrying the lookup.

    Returns ModelLifecycle if the model is deprecated/retiring, None otherwise.
    """
    result = DEPRECATION_REGISTRY.get(model)
    if result is not None:
        return result

    # Try stripping date suffix (e.g. "claude-3.5-sonnet-20241022" -> "claude-3.5-sonnet")
    base = _DATE_SUFFIX_RE.sub("", model)
    if base != model:
        return DEPRECATION_REGISTRY.get(base)

    return None
