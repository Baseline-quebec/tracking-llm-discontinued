"""Registry of deprecated/retiring LLM models with lifecycle data.

Sources:
    OpenAI: https://platform.openai.com/docs/deprecations
    Anthropic: https://platform.claude.com/docs/en/about-claude/model-deprecations
    Google: https://ai.google.dev/gemini-api/docs/deprecations
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal


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

    # --- Anthropic: Shutdown (already retired) ---
    _add(
        "claude-3.5-sonnet",
        "anthropic",
        "shutdown",
        "2025-10-28",
        "claude-sonnet-4",
        note="Both v1 (20240620) and v2 (20241022) retired",
    )
    _add("claude-3-opus", "anthropic", "shutdown", "2026-01-05", "claude-opus-4")
    _add("claude-3-sonnet", "anthropic", "shutdown", "2025-07-21", "claude-sonnet-4")

    # --- Anthropic: Deprecated (retirement date set) ---
    _add(
        "claude-3.5-haiku",
        "anthropic",
        "deprecated",
        "2026-02-19",
        "claude-haiku-4-5",
    )

    # --- Google: Retiring ---
    _add(
        "gemini-2.0-flash",
        "google",
        "retiring",
        "2026-03-31",
        "gemini-2.5-flash",
    )
    _add(
        "gemini-1.5-pro",
        "google",
        "shutdown",
        "2025-09-23",
        "gemini-2.5-pro",
        note="gemini-1.5-pro-001/002 retired",
    )
    _add(
        "gemini-1.5-flash",
        "google",
        "shutdown",
        "2025-09-23",
        "gemini-2.5-flash",
        note="gemini-1.5-flash-001/002 retired",
    )
    _add(
        "gemini-pro",
        "google",
        "shutdown",
        "2025-02-15",
        "gemini-2.5-pro",
        note="Original Gemini 1.0 Pro, retired",
    )

    return registry


DEPRECATION_REGISTRY: dict[str, ModelLifecycle] = _build_registry()


def check_deprecation(model: str) -> ModelLifecycle | None:
    """Look up deprecation info for a model.

    Handles date-suffixed model names (e.g. "gpt-4o-2024-08-06" → "gpt-4o")
    by stripping the suffix and retrying the lookup.

    Returns ModelLifecycle if the model is deprecated/retiring, None otherwise.
    """
    result = DEPRECATION_REGISTRY.get(model)
    if result is not None:
        return result

    # Try stripping date suffix (e.g. "claude-3.5-sonnet-20241022" → "claude-3.5-sonnet")
    base = _DATE_SUFFIX_RE.sub("", model)
    if base != model:
        return DEPRECATION_REGISTRY.get(base)

    return None
