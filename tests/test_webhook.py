"""BDD step definitions for webhook notification tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from pytest_bdd import given, parsers, scenarios, then, when

from src.deprecations import DeprecatedModel
from src.issue_reporter import DeprecationAlert
from src.models import ScanMatch
from src.webhook import _build_payload, send_webhook


scenarios("features/webhook.feature")


def _make_lifecycle(
    model: str = "gpt-4o",
    provider: str = "openai",
    status: str = "retiring",
) -> DeprecatedModel:
    return DeprecatedModel(
        model=model,
        provider=provider,
        status=status,
        shutdown_date=date(2026, 10, 1),
    )


def _make_alerts(model: str = "gpt-4o") -> list[DeprecationAlert]:
    lifecycle = _make_lifecycle(model=model)
    return [
        DeprecationAlert(
            match=ScanMatch(
                provider="openai",
                model=model,
                match_type="llm",
                file="config.yml",
                line=2,
            ),
            lifecycle=lifecycle,
        ),
        DeprecationAlert(
            match=ScanMatch(
                provider="openai",
                model=model,
                match_type="llm",
                file="src/chain.py",
                line=15,
            ),
            lifecycle=lifecycle,
        ),
    ]


# --- Given steps ---


@given(
    parsers.cfparse('a webhook payload for model "{model}" in repo "{repo}"'),
    target_fixture="payload",
)
def given_payload(model: str, repo: str) -> dict[str, object]:
    alerts = _make_alerts(model)
    return _build_payload(
        repo_name=repo,
        lifecycle=alerts[0].lifecycle,
        alerts=alerts,
        issue_url="https://github.com/org/repo/issues/42",
        title=f"Modèle déprécié : {model}",
        body=f"## Le modèle `{model}` est retiring\n...",
        assignees=["davebulaval"],
    )


@given(
    "a webhook URL that returns HTTP 200",
    target_fixture="webhook_setup",
)
def given_url_200() -> dict[str, object]:
    return {"url": "https://example.com/webhook", "error": None, "status": 200}


@given(
    "a webhook URL that returns HTTP 500",
    target_fixture="webhook_setup",
)
def given_url_500() -> dict[str, object]:
    return {
        "url": "https://example.com/webhook",
        "error": HTTPError(
            "https://example.com/webhook",
            500,
            "Internal Server Error",
            {},
            None,  # type: ignore[arg-type]
        ),
        "status": None,
    }


@given(
    "a webhook URL that causes a network error",
    target_fixture="webhook_setup",
)
def given_url_network_error() -> dict[str, object]:
    return {
        "url": "https://example.com/webhook",
        "error": URLError("Connection refused"),
        "status": None,
    }


@given(
    "a webhook URL that times out",
    target_fixture="webhook_setup",
)
def given_url_timeout() -> dict[str, object]:
    return {
        "url": "https://example.com/webhook",
        "error": TimeoutError("timed out"),
        "status": None,
    }


# --- When steps ---


def _mock_urlopen(setup: dict[str, object]) -> MagicMock:
    mock = MagicMock()
    error = setup["error"]
    if error is not None:
        mock.side_effect = error
    else:
        response = MagicMock()
        response.status = setup["status"]
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        mock.return_value = response
    return mock


@when(
    "I send the webhook",
    target_fixture="webhook_result",
)
def send_webhook_normal(webhook_setup: dict[str, object]) -> dict[str, object]:
    mock = _mock_urlopen(webhook_setup)
    alerts = _make_alerts()
    with patch("src.webhook.urlopen", mock):
        result = send_webhook(
            url=str(webhook_setup["url"]),
            repo_name="org/repo",
            lifecycle=alerts[0].lifecycle,
            alerts=alerts,
            issue_url="https://github.com/org/repo/issues/42",
            title="Modèle déprécié : gpt-4o",
            body="## Le modèle `gpt-4o` est retiring",
            assignees=["davebulaval"],
        )
    return {"result": result, "urlopen_called": mock.called}


@when(
    "I send the webhook in dry-run mode",
    target_fixture="webhook_result",
)
def send_webhook_dry_run(webhook_setup: dict[str, object]) -> dict[str, object]:
    mock = _mock_urlopen(webhook_setup)
    alerts = _make_alerts()
    with patch("src.webhook.urlopen", mock):
        result = send_webhook(
            url=str(webhook_setup["url"]),
            repo_name="org/repo",
            lifecycle=alerts[0].lifecycle,
            alerts=alerts,
            issue_url="https://github.com/org/repo/issues/42",
            title="Modèle déprécié : gpt-4o",
            body="## Le modèle `gpt-4o` est retiring",
            assignees=["davebulaval"],
            dry_run=True,
        )
    return {"result": result, "urlopen_called": mock.called}


# --- Then steps ---


@then(
    parsers.cfparse('the payload should contain field "{field}" with value "{value}"'),
)
def check_payload_field_value(payload: dict[str, object], field: str, value: str) -> None:
    assert field in payload, f"Payload missing field '{field}'"
    assert str(payload[field]) == value, f"Expected {field}='{value}', got '{payload[field]}'"


@then(
    parsers.cfparse('the payload should contain field "{field}"'),
)
def check_payload_field_exists(payload: dict[str, object], field: str) -> None:
    assert field in payload, f"Payload missing field '{field}'"


@then(
    parsers.cfparse("the webhook result should be {expected}"),
)
def check_webhook_result(webhook_result: dict[str, object], expected: str) -> None:
    expected_bool = expected == "True"
    assert webhook_result["result"] is expected_bool, (
        f"Expected {expected_bool}, got {webhook_result['result']}"
    )


@then(
    "no HTTP request should have been made",
)
def check_no_http_request(webhook_result: dict[str, object]) -> None:
    assert not webhook_result["urlopen_called"], "urlopen should not have been called in dry-run"
