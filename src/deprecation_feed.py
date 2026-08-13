"""Fetch and parse the deprecations.info live feed.

Source: https://deprecations.info/v1/deprecations.json
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from src.deprecations import DeprecatedModel, DeprecationStatus

logger = logging.getLogger(__name__)

FEED_URL = "https://deprecations.info/v1/deprecations.json"
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
        try:
            req = urllib.request.Request(  # noqa: S310 - FEED_URL is a hardcoded https constant
                FEED_URL, headers={"User-Agent": "llm-scanner/1.0"}
            )
            with urllib.request.urlopen(req, timeout=FEED_TIMEOUT) as resp:  # noqa: S310
                data: list[dict[str, Any]] = json.loads(resp.read().decode())
            return _parse_feed(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return []


def _parse_feed(data: list[dict[str, Any]]) -> list[DeprecatedModel]:
    """Parse raw JSON entries into DeprecatedModel objects."""
    from src.deprecations import DeprecatedModel

    results: list[DeprecatedModel] = []
    for entry in data:
        provider_raw = entry.get("provider", "")
        internal_provider = PROVIDER_MAP.get(provider_raw)
        if internal_provider is None:
            continue

        model_id = entry.get("model_id", "")
        if not model_id:
            continue

        raw_date = entry.get("shutdown_date")
        shutdown_date = _parse_date(raw_date)
        if raw_date and shutdown_date is None:
            logger.warning(
                "Invalid shutdown_date '%s' for model '%s', skipping", raw_date, model_id
            )
            continue

        # Determine status from dates
        status: DeprecationStatus
        today = datetime.now(tz=UTC).date()
        if shutdown_date is not None and shutdown_date < today:
            status = "shutdown"
        elif shutdown_date is not None:
            status = "retiring"
        else:
            status = "deprecated"

        results.append(
            DeprecatedModel(
                model=model_id,
                provider=internal_provider,
                status=status,
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
