"""BDD step definitions for deprecation feed tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from pytest_bdd import given, scenarios, then, when

from src.deprecation_feed import fetch_deprecations


scenarios("features/deprecation_feed.feature")


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
        MagicMock(
            read=MagicMock(return_value=json.dumps(_SAMPLE_FEED).encode()),
            __enter__=lambda s: s,
            __exit__=MagicMock(return_value=False),
        ),
    ]
    mock = MagicMock(side_effect=responses)
    return mock


@given(
    "a feed endpoint that always fails",
    target_fixture="mock_urlopen",
)
def given_always_failing() -> MagicMock:
    return MagicMock(side_effect=OSError("Connection refused"))


@when(
    "I fetch deprecations",
    target_fixture="feed_result",
)
def fetch(mock_urlopen: MagicMock) -> list[object]:
    with (
        patch("src.deprecation_feed.urllib.request.urlopen", mock_urlopen),
        patch("src.deprecation_feed.time.sleep"),
    ):
        return fetch_deprecations()


@then("I should receive deprecation data")
def check_has_data(feed_result: list[object]) -> None:
    assert len(feed_result) > 0, "Expected data, got empty list"


@then("I should receive an empty list")
def check_empty(feed_result: list[object]) -> None:
    assert feed_result == [], f"Expected empty list, got {feed_result}"
