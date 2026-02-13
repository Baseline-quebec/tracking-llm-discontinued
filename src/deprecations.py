"""Registry of deprecated/retiring LLM models with lifecycle data.

Sources:
    https://platform.openai.com/docs/deprecations
    https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/model-retirements
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


DeprecationStatus = Literal["retiring", "deprecated", "shutdown"]


@dataclass(frozen=True)
class ModelLifecycle:
    """Lifecycle information for a deprecated or retiring model."""

    model: str
    provider: str
    status: DeprecationStatus
    shutdown_date: date | None = None
    replacement: str | None = None
    note: str = ""


def _build_registry() -> dict[str, ModelLifecycle]:
    """Build the model deprecation registry."""
    registry: dict[str, ModelLifecycle] = {}

    def _add(
        model: str,
        provider: str,
        status: DeprecationStatus,
        shutdown_date: str | None = None,
        replacement: str | None = None,
        note: str = "",
    ) -> None:
        registry[model] = ModelLifecycle(
            model=model,
            provider=provider,
            status=status,
            shutdown_date=date.fromisoformat(shutdown_date) if shutdown_date else None,
            replacement=replacement,
            note=note,
        )

    # --- OpenAI: Shutdown (already past end-of-life) ---
    _add("o1-preview", "openai", "shutdown", "2025-07-28", "o3")
    _add("o1-mini", "openai", "shutdown", "2025-10-27", "o4-mini")

    # --- OpenAI: Deprecated (end-of-life approaching) ---
    _add(
        "gpt-3.5-turbo",
        "openai",
        "deprecated",
        "2025-09-14",
        "gpt-4.1-mini",
        note="All gpt-3.5-turbo variants included",
    )

    # --- OpenAI: Retiring (announced, still functional) ---
    _add("gpt-4", "openai", "retiring", "2026-06-06", "gpt-4.1")
    _add("gpt-4-turbo", "openai", "retiring", "2026-06-06", "gpt-4.1")
    _add("gpt-4-turbo-preview", "openai", "retiring", "2026-06-06", "gpt-4.1")
    _add(
        "gpt-4o",
        "openai",
        "retiring",
        "2026-10-01",
        "gpt-4.1",
        note="Standard deployments retire 2026-03-31",
    )
    _add(
        "gpt-4o-mini",
        "openai",
        "retiring",
        "2026-10-01",
        "gpt-4.1-mini",
        note="Standard deployments retire 2026-03-31",
    )
    _add("o1", "openai", "retiring", "2026-07-15", "o3")

    # --- OpenAI Embeddings: Retiring ---
    _add(
        "text-embedding-ada-002",
        "openai",
        "retiring",
        "2027-04-15",
        "text-embedding-3-small",
        note="No retirement before April 2027",
    )

    return registry


DEPRECATION_REGISTRY: dict[str, ModelLifecycle] = _build_registry()


def check_deprecation(model: str) -> ModelLifecycle | None:
    """Look up deprecation info for a model.

    Returns ModelLifecycle if the model is deprecated/retiring, None otherwise.
    """
    return DEPRECATION_REGISTRY.get(model)
