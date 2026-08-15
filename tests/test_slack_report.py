"""BDD step definitions for the consolidated Slack report."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.slack_report import send_report


scenarios("features/slack_report.feature")

URL = "https://app.windmill.dev/api/r/baseline/conformite/rapport"
TOKEN = "jeton-de-test"  # noqa: S105 - valeur factice de test, aucun secret reel


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@given("Windmill is not configured")
def _not_configured(context: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WINDMILL_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WINDMILL_TOKEN", raising=False)


@given("only the Windmill URL is configured")
def _partially_configured(context: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """A half-configured webhook must behave like no webhook at all.

    Sending an unauthenticated request would fail anyway, but silently: the
    sweep would look like it reported when it did not.
    """
    monkeypatch.setenv("WINDMILL_WEBHOOK_URL", URL)
    monkeypatch.delenv("WINDMILL_TOKEN", raising=False)


@given("Windmill is configured")
def _configured(context: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WINDMILL_WEBHOOK_URL", URL)
    monkeypatch.setenv("WINDMILL_TOKEN", TOKEN)
    context["erreur"] = None


@given("Windmill returns HTTP 500")
def _http_error(context: dict[str, Any]) -> None:
    context["erreur"] = HTTPError(URL, 500, "Server Error", {}, None)  # type: ignore[arg-type]


@given("Windmill is unreachable")
def _unreachable(context: dict[str, Any]) -> None:
    context["erreur"] = URLError("connexion refusee")


def _envoyer(context: dict[str, Any], affected: int, scanned: int) -> None:
    reponse = MagicMock()
    reponse.status = 200
    reponse.read = MagicMock(return_value=b"")
    reponse.__enter__ = MagicMock(return_value=reponse)
    reponse.__exit__ = MagicMock(return_value=False)

    with patch("src.http.urlopen") as ouvrir:
        if context.get("erreur") is not None:
            ouvrir.side_effect = context["erreur"]
        else:
            ouvrir.return_value = reponse
        context["resultat"] = send_report(
            [{"depot": f"org/depot-{i}", "elements": [f"modele-{i}"]} for i in range(affected)],
            scanned,
        )
        context["appels"] = ouvrir


@when("I send the report")
def _send(context: dict[str, Any]) -> None:
    _envoyer(context, affected=1, scanned=82)


@when(parsers.parse("I send the report for {affected:d} affected repositories out of {scanned:d}"))
def _send_counts(context: dict[str, Any], affected: int, scanned: int) -> None:
    _envoyer(context, affected=affected, scanned=scanned)


def _charge(context: dict[str, Any]) -> dict[str, Any]:
    requete = context["appels"].call_args.args[0]
    return json.loads(requete.data.decode())


@then("no HTTP request should have been made")
def _no_request(context: dict[str, Any]) -> None:
    context["appels"].assert_not_called()


@then("the request should have been made")
def _request_made(context: dict[str, Any]) -> None:
    context["appels"].assert_called_once()


@then("the result should be False")
def _false(context: dict[str, Any]) -> None:
    assert context["resultat"] is False


@then(parsers.parse('the payload should declare the report type "{attendu}"'))
def _type(context: dict[str, Any], attendu: str) -> None:
    assert _charge(context)["type_rapport"] == attendu


@then(parsers.parse("the payload should list {attendu:d} repositories"))
def _liste(context: dict[str, Any], attendu: int) -> None:
    assert len(_charge(context)["depots"]) == attendu


@then(parsers.parse("the payload should declare {attendu:d} scanned repositories"))
def _scannes(context: dict[str, Any], attendu: int) -> None:
    assert _charge(context)["total_analyses"] == attendu


@then("the request should carry the Windmill token")
def _jeton(context: dict[str, Any]) -> None:
    requete = context["appels"].call_args.args[0]
    assert requete.get_header("Authorization") == f"Bearer {TOKEN}"
