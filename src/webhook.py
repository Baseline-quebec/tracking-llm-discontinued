"""HTTP webhook notifications for CRM integration.

The webhook fires once per issue actually created, so the receiver never sees a
duplicate for a model already tracked: issue creation is deduplicated upstream.

Authentication is a bearer token, kept separate from the URL on purpose. A
webhook URL is not a secret and belongs in a readable GitHub variable, so anyone
can audit where alerts are sent; the token is the secret. Storing the URL as a
secret is what made the previous integration fail silently for months, with a
403 nobody could diagnose because nobody could read the destination.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.http import request_json


if TYPE_CHECKING:
    from src.deprecations import DeprecatedModel
    from src.issue_reporter import DeprecationAlert

logger = logging.getLogger(__name__)

_WEBHOOK_TIMEOUT_SECONDS = 10
_HTTP_FORBIDDEN = 403


def send_webhook(
    url: str,
    repo_name: str,
    lifecycle: DeprecatedModel,
    alerts: list[DeprecationAlert],
    issue_url: str,
    title: str,
    body: str,
    assignees: list[str] | None = None,
    *,
    dry_run: bool = False,
) -> bool:
    """Send a webhook notification for a created issue.

    Reads the bearer token from LLM_SCAN_WEBHOOK_TOKEN when present. Without it
    the request goes out unauthenticated, which any protected endpoint answers
    with 403.

    Returns True on success, False on any error (never raises).
    """
    payload = _build_payload(
        repo_name=repo_name,
        lifecycle=lifecycle,
        alerts=alerts,
        issue_url=issue_url,
        title=title,
        body=body,
        assignees=assignees,
    )

    if dry_run:
        logger.info("[DRY RUN] Webhook payload: %s", json.dumps(payload, ensure_ascii=False))
        return True

    return _post(url, payload)


def _build_payload(
    *,
    repo_name: str,
    lifecycle: DeprecatedModel,
    alerts: list[DeprecationAlert],
    issue_url: str,
    title: str,
    body: str,
    assignees: list[str] | None = None,
) -> dict[str, object]:
    """Build a JSON-serializable webhook payload."""
    return {
        "repo_name": repo_name,
        "model": lifecycle.model,
        "provider": lifecycle.provider,
        "status": lifecycle.status,
        "shutdown_date": lifecycle.shutdown_date.isoformat() if lifecycle.shutdown_date else None,
        "affected_files": [
            {"file": alert.match.file, "line": alert.match.line} for alert in alerts
        ],
        "issue_url": issue_url,
        "issue_title": title,
        "issue_body": body,
        "assignees": assignees or [],
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def _post(url: str, payload: dict[str, object]) -> bool:
    """POST the payload as JSON to the webhook URL.

    Returns True on success (2xx), False on any error.
    """
    token = os.environ.get("LLM_SCAN_WEBHOOK_TOKEN", "").strip()
    response = request_json(url, payload=payload, token=token, timeout=_WEBHOOK_TIMEOUT_SECONDS)

    if response.ok:
        logger.info("Webhook POST to %s succeeded (HTTP %s)", url, response.status)
        return True

    if response.status is None:
        logger.warning("Webhook POST to %s failed: %s", url, response.erreur)
    elif response.status == _HTTP_FORBIDDEN and not token:
        logger.warning(
            "Webhook POST to %s returned HTTP 403 and no token was provided. "
            "Set LLM_SCAN_WEBHOOK_TOKEN if the destination requires authentication.",
            url,
        )
    else:
        logger.warning("Webhook POST to %s returned HTTP %d", url, response.status)
    return False
