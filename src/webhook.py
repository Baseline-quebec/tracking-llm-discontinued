"""HTTP webhook notifications for CRM integration."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import Request, urlopen


if TYPE_CHECKING:
    from src.deprecations import DeprecatedModel
    from src.issue_reporter import DeprecationAlert

logger = logging.getLogger(__name__)

_WEBHOOK_TIMEOUT_SECONDS = 10


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
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})  # noqa: S310

    try:
        with urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS) as response:  # noqa: S310
            status = response.status
    except (URLError, OSError, TimeoutError) as exc:
        logger.warning("Webhook POST to %s failed: %s", url, exc)
        return False

    if 200 <= status < 300:
        logger.info("Webhook POST to %s succeeded (HTTP %d)", url, status)
        return True

    logger.warning("Webhook POST to %s returned HTTP %d", url, status)
    return False
