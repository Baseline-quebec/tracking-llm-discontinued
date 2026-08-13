"""Jira ticket creation for the organisation-wide sweep.

One consolidated ticket per sweep, not one per repository: forty tickets at
Highest priority in a single morning is indistinguishable from noise, and the
first thing anyone does with noise is mute it.

Entirely optional. When the Jira environment variables are absent the sweep
still runs and still opens GitHub issues; only the ticket is skipped. This keeps
the sweep usable before Jira credentials are provisioned.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
LABEL = "modeles-deprecies"
PRIORITY = "Highest"


@dataclass(frozen=True)
class JiraConfig:
    """Credentials and target project, read from the environment."""

    base_url: str
    email: str
    api_token: str
    project_key: str

    @classmethod
    def from_env(cls) -> JiraConfig | None:
        """Build the configuration, or None when Jira is not configured."""
        values = {
            "base_url": os.environ.get("JIRA_BASE_URL", "").rstrip("/"),
            "email": os.environ.get("JIRA_EMAIL", ""),
            "api_token": os.environ.get("JIRA_API_TOKEN", ""),
            "project_key": os.environ.get("JIRA_PROJECT_KEY", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            logger.info("Jira not configured (missing %s), skipping ticket", ", ".join(missing))
            return None
        return cls(**values)

    @property
    def auth_header(self) -> str:
        """Return the Basic authentication header Jira Cloud expects."""
        raw = f"{self.email}:{self.api_token}".encode()
        return "Basic " + base64.b64encode(raw).decode()


def _request(
    config: JiraConfig,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Call the Jira REST API. Returns the parsed body, or None on failure."""
    url = f"{config.base_url}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(  # noqa: S310 - base_url comes from our own config
        url,
        data=data,
        method="POST" if data else "GET",
        headers={
            "Authorization": config.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            # json.loads est typé Any : on refuse explicitement une réponse qui
            # ne serait pas un objet JSON plutôt que de la laisser passer.
            body = json.loads(response.read().decode())
            return body if isinstance(body, dict) else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        logger.warning("Jira %s returned HTTP %s: %s", path, exc.code, detail)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Jira %s failed: %s", path, exc)
    return None


def open_ticket_exists(config: JiraConfig) -> bool:
    """True when an unresolved sweep ticket is already open.

    Without this check the monthly cron files a fresh Highest-priority ticket
    every month for the same unmigrated model, and the backlog fills with
    duplicates of a problem already tracked.
    """
    jql = f'project = "{config.project_key}" AND labels = "{LABEL}" AND statusCategory != Done'
    body = _request(config, "/rest/api/3/search/jql", {"jql": jql, "maxResults": 1, "fields": []})
    if body is None:
        return False
    issues = body.get("issues")
    return bool(isinstance(issues, list) and issues)


def _document(summary_markdown: str) -> dict[str, object]:
    """Wrap the summary in the Atlassian Document Format Jira expects."""
    paragraphs = [line for line in summary_markdown.splitlines() if line.strip()]
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            for line in paragraphs
        ],
    }


def create_ticket(summary_markdown: str, affected_repositories: int) -> str | None:
    """File the consolidated ticket. Returns the issue key, or None."""
    config = JiraConfig.from_env()
    if config is None:
        return None

    if open_ticket_exists(config):
        logger.info("A sweep ticket is already open, skipping creation")
        return None

    title = (
        f"Modèles LLM dépréciés référencés dans {affected_repositories} dépôt(s) de l'organisation"
    )
    fields: dict[str, object] = {
        "project": {"key": config.project_key},
        "summary": title,
        "description": _document(summary_markdown),
        "issuetype": {"name": "Task"},
        "labels": [LABEL],
        "priority": {"name": PRIORITY},
    }

    body = _request(config, "/rest/api/3/issue", {"fields": fields})
    if body is None:
        # Team-managed projects often have no priority field at all, and Jira
        # rejects the whole request rather than ignoring the unknown field.
        # Retrying without it is better than losing the ticket entirely.
        logger.info("Retrying Jira ticket creation without the priority field")
        fields.pop("priority")
        body = _request(config, "/rest/api/3/issue", {"fields": fields})

    if body is None:
        logger.error("Could not create the Jira ticket")
        return None

    key = str(body.get("key", ""))
    logger.info("Created Jira ticket %s", key)
    return key or None
