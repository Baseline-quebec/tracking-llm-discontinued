"""Sends the consolidated sweep report to Slack, through Windmill.

The formatting lives in `baseline-automation`, not here: that is where the
Slack token and the team's reporting conventions already are. This module only
ships the structured result to the Windmill script that posts it, so the two
monthly reports (deprecated models, dependency licences) render identically
without duplicating any layout code.

Entirely optional. When the Windmill environment variables are absent the sweep
still runs and still opens GitHub issues; only the Slack message is skipped.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from src.http import request_json


logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
REPORT_TYPE = "modeles"


@dataclass(frozen=True)
class WindmillConfig:
    """Webhook target and credential, read from the environment."""

    webhook_url: str
    token: str

    @classmethod
    def from_env(cls) -> WindmillConfig | None:
        """Build the configuration, or None when Windmill is not configured."""
        webhook_url = os.environ.get("WINDMILL_WEBHOOK_URL", "").strip()
        token = os.environ.get("WINDMILL_TOKEN", "").strip()
        missing = [
            name
            for name, value in (("WINDMILL_WEBHOOK_URL", webhook_url), ("WINDMILL_TOKEN", token))
            if not value
        ]
        if missing:
            logger.info("Windmill not configured (missing %s), skipping Slack report", missing)
            return None
        return cls(webhook_url=webhook_url, token=token)


def send_report(
    repositories: list[dict[str, object]],
    total_scanned: int,
    *,
    report_type: str = REPORT_TYPE,
    channel_id: str = "",
) -> bool:
    """Post the consolidated report. Returns True when Slack received it.

    A failure here never fails the sweep: the GitHub issues are the record of
    truth, the Slack message is a courtesy notification. Losing the message is
    an annoyance; losing the sweep because Slack was unreachable is not.
    """
    config = WindmillConfig.from_env()
    if config is None:
        return False

    payload = {
        "type_rapport": report_type,
        "depots": repositories,
        "total_analyses": total_scanned,
        "channel_id": channel_id,
    }
    response = request_json(
        config.webhook_url,
        payload=payload,
        token=config.token,
        timeout=TIMEOUT_SECONDS,
    )

    if response.ok:
        logger.info("Slack report sent (HTTP %s)", response.status)
        return True
    if response.status is None:
        logger.warning("Could not reach Windmill: %s", response.erreur)
    else:
        logger.warning("Windmill returned HTTP %s: %s", response.status, response.body[:300])
    return False
