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
# Fenetre autour d'une correspondance ou le mot-cle de contexte doit se trouver.
# Large assez pour `openai_client.embeddings.create(model="ada")`, trop etroite
# pour une phrase de prose qui mentionne une API quarante mots plus loin.
CONTEXT_WINDOW = 40

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
        r"\bgpt-5(?:\.\d)?(?:-(?:mini|nano|pro|codex|chat))?"
        r"(?:-(?:latest|mini|max)|-\d{4}-\d{2}-\d{2})?\b",
    )
    _add("openai", "llm", r"\bgpt-4\.5-preview\b")
    _add("openai", "llm", r"\bgpt-4\.1(?:-(?:mini|nano))?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o-audio(?:-preview)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o-realtime(?:-preview)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o-search-preview(?:-\d{4}-\d{2}-\d{2})?\b")
    _add(
        "openai",
        "llm",
        r"\bgpt-4o-mini-(?:audio|realtime|search)(?:-preview)?(?:-\d{4}-\d{2}-\d{2})?\b",
    )
    _add("openai", "llm", r"\bgpt-4o-mini-(?:tts|transcribe)(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-4o(?:-mini)?(?:-\d{4}-\d{2}-\d{2})?\b")
    # Suffixe `-completions` : identifiants d'endpoint publies par deprecations.info
    # (ex: gpt-4-turbo-completions), distincts du modele servi via /chat/completions.
    _add("openai", "llm", r"\bgpt-4-turbo(?:-preview)?(?:-\d{4}-\d{2}-\d{2})?(?:-completions)?\b")
    _add("openai", "llm", r"\bgpt-4-vision-preview\b")
    _add("openai", "llm", r"\bgpt-4-\d{4}-vision-preview\b")
    _add("openai", "llm", r"\bgpt-4-\d{4}-preview\b")
    # gpt-4-MMDD: negative lookahead prevents matching YYYY-MM-DD date suffixes
    _add("openai", "llm", r"\bgpt-4-\d{4}(?!-\d{2}-\d{2})(?:-completions)?\b")
    _add("openai", "llm", r"\bgpt-4-32k-\d{4}\b")
    # gpt-4 base: negative lookahead prevents matching gpt-4.1, gpt-4.5, gpt-4o, gpt-4-turbo
    _add(
        "openai",
        "llm",
        r"\bgpt-4(?!\.\d|o|-turbo)(?:-32k)?(?:-\d{4}-\d{2}-\d{2})?(?:-completions)?\b",
    )
    _add("openai", "llm", r"\bgpt-3\.5-turbo-instruct\b")
    _add("openai", "llm", r"\bgpt-3\.5-turbo-16k(?:-\d{4})?\b")
    _add("openai", "llm", r"\bgpt-3\.5-turbo(?:-\d{4})?(?:-completions)?\b")
    _add("openai", "llm", r"\bgpt-(?:audio|realtime)(?:-mini)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bgpt-image-\d+(?:\.\d+)?(?:-mini)?\b")
    _add("openai", "llm", r"\bchatgpt-(?:4o|image)-latest\b")
    _add(
        "openai",
        "llm",
        r"\bo1(?:-preview|-mini|-pro)?(?:-\d{4}-\d{2}-\d{2})?\b",
        context_required=True,
    )
    _add(
        "openai",
        "llm",
        r"\bo3(?:-mini|-pro|-deep-research)?(?:-\d{4}-\d{2}-\d{2})?\b",
        context_required=True,
    )
    _add("openai", "llm", r"\bo4-mini(?:-deep-research)?(?:-\d{4}-\d{2}-\d{2})?\b")
    _add("openai", "llm", r"\bcodex-mini(?:-latest)?\b")
    _add(
        "openai",
        "llm",
        r"\bcomputer-use-preview(?:-\d{4}-\d{2}-\d{2})?\b",
        context_required=True,
    )
    _add("openai", "llm", r"\bdall-e-[23]\b")
    _add("openai", "llm", r"\bsora-\d+(?:-pro)?(?:-\d{4}-\d{2}-\d{2})?\b")
    # Fine-tuned model variants (ft- prefix)
    _add(
        "openai",
        "llm",
        r"\bft-(?:gpt-4\.1-(?:mini|nano)-\d{4}-\d{2}-\d{2}|gpt-3\.5-turbo|gpt-4|"
        r"babbage-\d{3}|davinci-\d{3}|o4-mini-\d{4}-\d{2}-\d{2})\b",
    )
    # Legacy text generation models
    _add("openai", "llm", r"\btext-(?:ada|babbage|curie|davinci)-\d{3}\b")
    _add("openai", "llm", r"\btext-davinci-edit-\d{3}\b")
    _add("openai", "llm", r"\btext-moderation(?:-(?:\d{3}|latest|stable))?\b")
    # Legacy code models
    _add("openai", "llm", r"\bcode-(?:cushman|davinci)-\d{3}\b")
    _add("openai", "llm", r"\bcode-davinci-edit-\d{3}\b")
    _add("openai", "llm", r"\bcode-search-(?:ada|babbage)-(?:code|text)-\d{3}\b")
    # Legacy search and similarity
    _add("openai", "llm", r"\btext-search-(?:ada|babbage|curie|davinci)-(?:doc|query)-\d{3}\b")
    _add("openai", "llm", r"\btext-similarity-(?:ada|babbage|curie|davinci)-\d{3}\b")
    # Generic legacy base models (require context; lookbehind prevents matching within compound
    # names like text-embedding-ada-002 where ada appears after a dash separator)
    _add("openai", "llm", r"(?<![a-z0-9-])ada\b", context_required=True)
    _add("openai", "llm", r"(?<![a-z0-9-])babbage(?:-\d{3})?\b", context_required=True)
    _add("openai", "llm", r"(?<![a-z0-9-])curie\b", context_required=True)
    _add("openai", "llm", r"(?<![a-z0-9-])davinci(?:-\d{3})?\b", context_required=True)

    # --- Anthropic ---
    # Le point de version mineur est un tiret chez Anthropic : claude-opus-4-1-20250805.
    _add("anthropic", "llm", r"\bclaude-opus-4(?:-\d)?(?:-\d{8})?\b")
    _add("anthropic", "llm", r"\bclaude-sonnet-4(?:-\d)?(?:-\d{8})?\b")
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
    _add("google", "llm", r"\bgemini-3(?:[\.-]\d+)?-(?:pro|flash)(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-robotics-er-\d+[\.-]\d+(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]5-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]5-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]0-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-2[\.-]0-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]5-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]5-flash(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-1[\.-]0-pro(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bgemini-pro\b")
    _add("google", "llm", r"\bgemini-live(?:-[a-z0-9.]+)*\b")
    _add("google", "llm", r"\bimagen-\d+\.\d+(?:-[a-z0-9]+)*\b")
    _add("google", "llm", r"\bveo-\d+\.\d+(?:-[a-z0-9]+)*\b")

    # --- Google Embeddings ---
    _add("google", "embedding", r"\bgemini-embedding(?:-[a-z0-9]+)*\b")
    # Anciens identifiants PaLM/Gemini sans prefixe de famille. Le lookbehind evite
    # de re-matcher la fin de `gemini-embedding-001` ou `text-embedding-004`.
    _add("google", "embedding", r"(?<![a-z0-9-])embedding-(?:gecko-)?\d{3}\b")
    _add("google", "embedding", r"(?<![a-z0-9-])embedding-\d+-preview\b")
    _add("google", "embedding", r"\btext-embedding-\d{3}\b")

    # --- OpenAI Embeddings ---
    _add("openai", "embedding", r"\btext-embedding-3-(?:small|large)\b")
    _add("openai", "embedding", r"\btext-embedding-ada-002\b")

    # --- Voyage Embeddings ---
    _add("voyage", "embedding", r"\bvoyage-(?:[a-z]+-)*\d+(?:-[a-z0-9]+)*\b")

    return patterns


MODEL_PATTERNS: list[ModelPattern] = _build_patterns()


def _has_nearby_context(line: str, match: re.Match[str]) -> bool:
    """Vrai si un mot-cle de contexte entoure la correspondance de pres.

    Chercher le mot-cle n'importe ou dans la ligne suffisait a valider des noms
    de modeles courts comme `ada` des qu'un mot banal apparaissait ailleurs.
    Cas reel : « Ada-inc has two imports ... needs to post sales to an API »,
    dans le README de Monolog, ou « API » se trouve a quatre-vingt-dix
    caracteres de « Ada ». Une vraie declaration met le mot-cle a cote :
    `model="ada"`, `"engine": "ada"`.
    """
    debut = max(0, match.start() - CONTEXT_WINDOW)
    fin = min(len(line), match.end() + CONTEXT_WINDOW)
    return CONTEXT_KEYWORDS.search(line[debut:fin]) is not None


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

        if model_pattern.context_required and not _has_nearby_context(line, match):
            continue

        model_name = match.group(0).lower()
        results.append((model_pattern.provider, model_name, model_pattern.match_type))

    return results
