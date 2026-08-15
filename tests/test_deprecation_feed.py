"""BDD step definitions for deprecation feed tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecation_feed import fetch_deprecations


scenarios("features/deprecation_feed.feature")


def _reponse_ok(feed: list[dict[str, str]]) -> MagicMock:
    """Reponse HTTP 200 dont le corps est le flux serialise."""
    reponse = MagicMock()
    reponse.status = 200
    reponse.read = MagicMock(return_value=json.dumps(feed).encode())
    reponse.__enter__ = MagicMock(return_value=reponse)
    reponse.__exit__ = MagicMock(return_value=False)
    return reponse


_SAMPLE_FEED = [
    {
        "provider": "OpenAI",
        "model_id": "gpt-4o",
        "shutdown_date": "2026-10-01",
    },
]


@given(
    "a feed endpoint that fails 2 times then succeeds",
    target_fixture="mock_urlopen",
)
def given_transient_failures() -> MagicMock:
    responses: list[object] = [
        OSError("Connection refused"),
        OSError("Connection reset"),
        _reponse_ok(_SAMPLE_FEED),
    ]
    mock = MagicMock(side_effect=responses)
    return mock


@given(
    "a feed endpoint that always fails",
    target_fixture="mock_urlopen",
)
def given_always_failing() -> MagicMock:
    return MagicMock(side_effect=OSError("Connection refused"))


@given(
    parsers.cfparse('a feed endpoint returning the category header "{header}"'),
    target_fixture="mock_urlopen",
)
def given_category_header(header: str) -> MagicMock:
    """Simule un flux ne renvoyant qu'un entete de section.

    Le flux melange des model IDs et des entetes, reconnaissables a leur espace.
    Les laisser passer polluait le registre d'entrees que load_registry rejette
    ensuite une par une, avec un avertissement a chaque appel.
    """
    feed = [{"provider": "OpenAI", "model_id": header, "shutdown_date": "2026-06-03"}]
    return MagicMock(return_value=_reponse_ok(feed))


@when(
    "I fetch deprecations",
    target_fixture="feed_result",
)
def fetch(mock_urlopen: MagicMock) -> list[object]:
    with (
        patch("src.http.urlopen", mock_urlopen),
        patch("src.deprecation_feed.time.sleep"),
    ):
        return fetch_deprecations()


@then("I should receive deprecation data")
def check_has_data(feed_result: list[object]) -> None:
    assert len(feed_result) > 0, "Expected data, got empty list"


@then("I should receive an empty list")
def check_empty(feed_result: list[object]) -> None:
    assert feed_result == [], f"Expected empty list, got {feed_result}"
