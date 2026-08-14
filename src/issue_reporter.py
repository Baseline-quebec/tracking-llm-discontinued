"""GitHub Issue creation for deprecated model alerts."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.webhook import send_webhook


if TYPE_CHECKING:
    from src.deprecations import DeprecatedModel
    from src.models import ScanMatch


logger = logging.getLogger(__name__)

ISSUE_LABEL = "deprecated-model"
GH_TIMEOUT_SECONDS = 30

# Only allow safe model names (lowercase alphanumeric, dots, hyphens)
_SAFE_MODEL_NAME = re.compile(r"^[a-z0-9.\-]+$")

# GitHub username: alphanumeric or hyphens, cannot start/end with hyphen
_GITHUB_USERNAME = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?$")


@dataclass(frozen=True)
class DeprecationAlert:
    """A deprecated model reference found in the codebase."""

    match: ScanMatch
    lifecycle: DeprecatedModel


def create_issues(
    alerts: list[DeprecationAlert],
    assignees: list[str] | None = None,
    *,
    dry_run: bool = False,
    webhook_url: str | None = None,
    repo_name: str = "",
    target_repo: str | None = None,
) -> tuple[int, int]:
    """Create GitHub issues for deprecated models.

    Groups alerts by model so each model gets at most one issue.
    Skips creation if an open issue already exists for the model.

    `target_repo` routes every gh call to an explicit repository, which the
    organisation-wide sweep needs since it scans clones rather than the
    checkout it runs from. Left as None, gh infers the repository from the
    working directory, which is the behaviour the per-repo action relies on.

    Returns (issues_created, issues_failed).
    """
    if not alerts:
        return 0, 0

    # Validate assignees
    valid_assignees = _validate_assignees(assignees) if assignees else None

    if not dry_run:
        _ensure_label(target_repo)

    by_model: dict[str, list[DeprecationAlert]] = {}
    for alert in alerts:
        by_model.setdefault(alert.lifecycle.model, []).append(alert)

    created = 0
    failed = 0
    for model, model_alerts in by_model.items():
        # The existence check runs in dry-run too. It is read-only, and skipping
        # it made the rehearsal count every alert as new: the estimate came out
        # far above what a real run would file, which is the opposite of what a
        # rehearsal is for.
        if _issue_exists(model, target_repo):
            logger.info("Open issue already exists for %s, skipping", model)
            continue

        lifecycle = model_alerts[0].lifecycle
        title = _build_title(lifecycle)
        body = _build_body(lifecycle, model_alerts)

        if dry_run:
            logger.info("[DRY RUN] Would create issue: %s", title)
            if webhook_url:
                send_webhook(
                    url=webhook_url,
                    repo_name=repo_name,
                    lifecycle=lifecycle,
                    alerts=model_alerts,
                    issue_url="",
                    title=title,
                    body=body,
                    assignees=valid_assignees,
                    dry_run=True,
                )
            created += 1
            continue

        issue_url = _create_issue(title, body, valid_assignees, target_repo)
        if issue_url:
            created += 1
            if webhook_url:
                send_webhook(
                    url=webhook_url,
                    repo_name=repo_name,
                    lifecycle=lifecycle,
                    alerts=model_alerts,
                    issue_url=issue_url,
                    title=title,
                    body=body,
                    assignees=valid_assignees,
                )
        else:
            failed += 1

    return created, failed


def _validate_assignees(assignees: list[str]) -> list[str] | None:
    """Filter assignees to only valid GitHub usernames."""
    valid = [a for a in assignees if _GITHUB_USERNAME.match(a)]
    invalid = [a for a in assignees if not _GITHUB_USERNAME.match(a)]
    if invalid:
        logger.warning("Skipping invalid GitHub usernames: %s", invalid)
    return valid or None


def _repo_flag(target_repo: str | None) -> list[str]:
    """Build the gh --repo flag, or nothing when the current directory decides."""
    return ["--repo", target_repo] if target_repo else []


def _ensure_label(target_repo: str | None = None) -> None:
    """Create the deprecated-model label if it doesn't exist."""
    try:
        result = subprocess.run(
            [
                "gh",
                "label",
                "create",
                ISSUE_LABEL,
                "--description",
                "Model deprecation alert",
                "--color",
                "D93F0B",
                "--force",
                *_repo_flag(target_repo),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout creating label '%s'", ISSUE_LABEL)
        return
    if result.returncode != 0 and "already exists" not in result.stderr:
        logger.warning("Could not create label '%s': %s", ISSUE_LABEL, result.stderr)


def _issue_exists(model: str, target_repo: str | None = None) -> bool:
    """Check if an open issue already exists for this model.

    Uses GitHub search to find candidates, then verifies the model name
    appears in the title to avoid false positives from fuzzy search.
    """
    if not _SAFE_MODEL_NAME.match(model):
        logger.warning("Suspicious model name, skipping search: %s", model)
        return False

    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--label",
                ISSUE_LABEL,
                "--search",
                f'"{model}" in:title',
                "--state",
                "open",
                "--json",
                "number,title",
                *_repo_flag(target_repo),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout searching issues for '%s'", model)
        return False
    if result.returncode != 0:
        logger.warning("Failed to search issues: %s", result.stderr)
        return False

    try:
        issues: list[dict[str, str | int]] = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("Failed to parse issue list response: %s", result.stdout[:200])
        return False

    # Verify the title matches exactly: a substring check would falsely match
    # e.g. "gpt-4" against an open issue titled "Modèle déprécié : gpt-4o".
    expected_title = _build_title_for_model(model)
    return any(str(issue.get("title", "")) == expected_title for issue in issues)


def _create_issue(
    title: str,
    body: str,
    assignees: list[str] | None = None,
    target_repo: str | None = None,
) -> str | None:
    """Create a single GitHub issue. Returns the issue URL on success, None on failure."""
    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--label",
        ISSUE_LABEL,
        *_repo_flag(target_repo),
    ]
    if assignees:
        cmd.extend(["--assignee", ",".join(assignees)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout creating issue '%s'", title)
        return None
    if result.returncode == 0:
        issue_url = result.stdout.strip()
        logger.info("Created issue: %s → %s", title, issue_url)
        return issue_url
    logger.error("Failed to create issue '%s': %s", title, result.stderr)
    return None


def _build_title_for_model(model: str) -> str:
    """Build the issue title from a model name."""
    return f"Modèle déprécié : {model}"


def _build_title(lifecycle: DeprecatedModel) -> str:
    """Build the issue title."""
    return _build_title_for_model(lifecycle.model)


def _build_body(
    lifecycle: DeprecatedModel,
    alerts: list[DeprecationAlert],
) -> str:
    """Build the issue body in Markdown."""
    lines = [
        f"## Le modèle `{lifecycle.model}` est {lifecycle.status}",
        "",
        f"**Provider :** {lifecycle.provider}",
        f"**Statut :** {lifecycle.status}",
    ]

    if lifecycle.shutdown_date:
        lines.append(f"**Date d'arrêt :** {lifecycle.shutdown_date.isoformat()}")

    lines.extend(["", "### Fichiers affectés", ""])
    lines.append("| Fichier | Ligne |")
    lines.append("|---------|-------|")
    lines.extend(f"| `{alert.match.file}` | {alert.match.line} |" for alert in alerts)

    lines.extend(
        [
            "",
            "### Action requise",
            "Migrer vers un modèle supporté avant la date d'arrêt.",
            "",
            "---",
            "*Cette issue a été créée automatiquement par le LLM Configuration Scanner.*",
        ]
    )

    return "\n".join(lines)
