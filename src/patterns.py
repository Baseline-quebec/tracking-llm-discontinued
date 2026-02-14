"""Regex patterns for detecting LLM models and embeddings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.models import MatchType


@dataclass(frozen=True)
class ModelPattern:
    """A pattern definition for detecting a model reference."""

    provider: str
    match_type: MatchType
    pattern: re.Pattern[str]
    context_required: bool = False


# Context keywords required for short model names (e.g. "o1", "o3")
CONTEXT_KEYWORDS: re.Pattern[str] = re.compile(
    r"model|llm|openai|api|chat|completion|gpt|anthropic|claude|gemini|google|"
    r"embedding|embed|vector|provider|ai[\._\-]|engine",
    re.IGNORECASE,
)


def _build_patterns() -> list[ModelPattern]:
    """Build all model detection patterns."""
    patterns: list[ModelPattern] = []

    def _add(
        provider: str,
        match_type: MatchType,
        regex: str,
        *,
        context_required: bool = False,
    ) -> None:
        patterns.append(
            ModelPattern(
                provider=provider,
                match_type=match_type,
                pattern=re.compile(regex, re.IGNORECASE),
                context_required=context_required,
            )
        )

    # --- OpenAI LLM ---
    _add(
        "openai",
        "llm",
        r"\bgpt-5(?:\.[12])?(?:-(?:mini|nano|pro|codex|chat))?(?:-\d{4}-\d{2}-\d{2})?\b",
    )
    _add("openai", "llm", r"\bgpt-4\.5-preview\b")
    _add("openai", "llm", r"\bgpt-4\.1(?:-(?:mini|nano))?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o-audio-preview(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o-realtime-preview(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o(?:-mini)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4-turbo(?:-preview)?(?:-\d{4}-\d{2}-\d{2})?\b")
    # gpt-4 base: negative lookahead prevents matching gpt-4.1, gpt-4.5, gpt-4o, gpt-4-turbo
    _add("openai", "llm", r"\bgpt-4(?!\.\d|o|-turbo)(?:-32k)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-3\.5-turbo(?:-\d{4})?\b")
    _add("openai", "llm", r"\bchatgpt-4o-latest\b")
    _add("openai", "llm", r"\bo1(?:-preview|-mini|-pro)?\b", context_required=True)
    _add("openai", "llm", r"\bo3(?:-mini|-pro|-deep-research)?\b", context_required=True)
    _add("openai", "llm", r"\bo4-mini\b")
    _add("openai", "llm", r"\bcodex-mini(?:-latest)?\b")
    _add("openai", "llm", r"\btext-moderation\b")

    # --- Anthropic ---
    _add("anthropic", "llm", r"\bclaude-opus-4\b")
    _add("anthropic", "llm", r"\bclaude-sonnet-4\b")
    _add("anthropic", "llm", r"\bclaude-3[\.-]7-sonnet(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-3[\.-]5-sonnet(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-3[\.-]5-haiku(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-3-opus(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-3-sonnet(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-3-haiku(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-2\.\d\b")
    _add("anthropic", "llm", r"\bclaude-instant-1\.\d\b")
    _add("anthropic", "llm", r"\bclaude-1\.\d\b")

    # --- Google LLM ---
    _add("google", "llm", r"\bgemini-2[\.-]5-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]5-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]0-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]0-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]5-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]5-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]0-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-pro\b")
    _add("google", "llm", r"\bgemini-live(?:-[a-z0-9.]+)+\b")
    _add("google", "llm", r"\bimagen-\d+\.\d+(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bveo-\d+\.\d+(?:-[a-z0-9]+)*\b")

    # --- Google Embeddings ---
    _add("google", "embedding", r"\bgemini-embedding(?:-[a-z0-9]+)*\b")

    # --- OpenAI Embeddings ---
    _add("openai", "embedding", r"\btext-embedding-3-(?:small|large)\b")
    _add("openai", "embedding", r"\btext-embedding-ada-002\b")

    # --- Voyage Embeddings ---
    _add("voyage", "embedding", r"\bvoyage-(?:large|code|lite)-\d+\b")

    return patterns


MODEL_PATTERNS: list[ModelPattern] = _build_patterns()


def find_matches_in_line(
    line: str,
) -> list[tuple[str, str, MatchType]]:
    """Find all model/embedding matches in a single line of text.

    Returns a list of (provider, model_name, match_type) tuples.
    """
    results: list[tuple[str, str, MatchType]] = []

    for model_pattern in MODEL_PATTERNS:
        match: re.Match[str] | None = model_pattern.pattern.search(line)
        if match is None:
            continue

        if model_pattern.context_required and not CONTEXT_KEYWORDS.search(line):
            continue

        model_name = match.group(0).lower()
        results.append((model_pattern.provider, model_name, model_pattern.match_type))

    return results
