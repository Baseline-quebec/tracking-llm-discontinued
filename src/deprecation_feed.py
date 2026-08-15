"""Fetch and parse the deprecations.info live feed.

Source: https://deprecations.info/v1/deprecations.json
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from typing import TYPE_CHECKING, Any

from src.http import request_json


if TYPE_CHECKING:
    from src.deprecations import DeprecatedModel

logger = logging.getLogger(__name__)

FEED_URL = "https://deprecations.info/v1/deprecations.json"
USER_AGENT = "llm-scanner/1.0"
FEED_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Providers we track (feed name -> internal name)
PROVIDER_MAP: dict[str, str] = {
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "Google": "google",
}


def fetch_deprecations() -> list[DeprecatedModel]:
    """Fetch deprecation data from deprecations.info.

    Retries up to MAX_RETRIES times with RETRY_DELAY seconds between attempts.
    Returns a list of DeprecatedModel objects for tracked providers.
    Returns an empty list on any network or parsing error (silent fallback).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        response = request_json(FEED_URL, timeout=FEED_TIMEOUT, user_agent=USER_AGENT)
        if response.ok:
            try:
                data: list[dict[str, Any]] = json.loads(response.body)
            except json.JSONDecodeError as exc:
                logger.warning("Attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            else:
                return _parse_feed(data)
        else:
            logger.warning(
                "Attempt %d/%d failed: %s",
                attempt,
                MAX_RETRIES,
                response.erreur or response.status,
            )
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    return []


def _parse_feed(data: list[dict[str, Any]]) -> list[DeprecatedModel]:
    """Parse raw JSON entries into DeprecatedModel objects."""
    from src.deprecations import DeprecatedModel, status_for

    results: list[DeprecatedModel] = []
    for entry in data:
        provider_raw = entry.get("provider", "")
        internal_provider = PROVIDER_MAP.get(provider_raw)
        if internal_provider is None:
            continue

        model_id = entry.get("model_id", "")
        if not model_id:
            continue

        # Le flux melange des model IDs et des entetes de categorie
        # ("Agent Builder", "Reusable prompts"). Les ecrire dans le registre
        # revenait a faire rejeter l'entree par load_registry a chaque appel,
        # avec un avertissement, et a gonfler le fichier de lignes mortes.
        if " " in model_id:
            logger.info("Entete de categorie ignoree : %s", model_id)
            continue

        raw_date = entry.get("shutdown_date")
        shutdown_date = _parse_date(raw_date)
        if raw_date and shutdown_date is None:
            logger.warning(
                "Invalid shutdown_date '%s' for model '%s', skipping", raw_date, model_id
            )
            continue

        results.append(
            DeprecatedModel(
                model=model_id,
                provider=internal_provider,
                status=status_for(shutdown_date),
                shutdown_date=shutdown_date,
            )
        )

    logger.info("Fetched %d deprecations from feed (%d tracked)", len(data), len(results))
    return results


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO date string, returning None for empty/invalid values."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
