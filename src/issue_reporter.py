"""GitHub Issue creation for deprecated model alerts."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.deprecations import ModelLifecycle
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
    lifecycle: ModelLifecycle


def create_issues(
    alerts: list[DeprecationAlert],
    assignees: list[str] | None = None,
    *,
    dry_run: bool = False,
) -> int:
    """Create GitHub issues for deprecated models.

    Groups alerts by model so each model gets at most one issue.
    Skips creation if an open issue already exists for the model.

    Returns the number of new issues created.
    """
    if not alerts:
        return 0

    # Validate assignees
    valid_assignees = _validate_assignees(assignees) if assignees else None

    if not dry_run:
        _ensure_label()

    by_model: dict[str, list[DeprecationAlert]] = {}
    for alert in alerts:
        by_model.setdefault(alert.lifecycle.model, []).append(alert)

    created = 0
    for model, model_alerts in by_model.items():
        if not dry_run and _issue_exists(model):
            logger.info("Open issue already exists for %s, skipping", model)
            continue

        lifecycle = model_alerts[0].lifecycle
        title = _build_title(lifecycle)
        body = _build_body(lifecycle, model_alerts)

        if dry_run:
            logger.info("[DRY RUN] Would create issue: %s", title)
            created += 1
            continue

        if _create_issue(title, body, valid_assignees):
            created += 1

    return created


def _validate_assignees(assignees: list[str]) -> list[str] | None:
    """Filter assignees to only valid GitHub usernames."""
    valid = [a for a in assignees if _GITHUB_USERNAME.match(a)]
    invalid = [a for a in assignees if not _GITHUB_USERNAME.match(a)]
    if invalid:
        logger.warning("Skipping invalid GitHub usernames: %s", invalid)
    return valid or None


def _ensure_label() -> None:
    """Create the deprecated-model label if it doesn't exist."""
    result = subprocess.run(  # noqa: S603
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
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=GH_TIMEOUT_SECONDS,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        logger.warning("Could not create label '%s': %s", ISSUE_LABEL, result.stderr)


def _issue_exists(model: str) -> bool:
    """Check if an open issue already exists for this model."""
    if not _SAFE_MODEL_NAME.match(model):
        logger.warning("Suspicious model name, skipping search: %s", model)
        return False

    result = subprocess.run(  # noqa: S603
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
            "number",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=GH_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        logger.warning("Failed to search issues: %s", result.stderr)
        return False

    try:
        issues: list[dict[str, int]] = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("Failed to parse issue list response: %s", result.stdout[:200])
        return False

    return len(issues) > 0


def _create_issue(
    title: str,
    body: str,
    assignees: list[str] | None = None,
) -> bool:
    """Create a single GitHub issue. Returns True on success."""
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
    ]
    if assignees:
        cmd.extend(["--assignee", ",".join(assignees)])

    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=GH_TIMEOUT_SECONDS,
    )
    if result.returncode == 0:
        logger.info("Created issue: %s → %s", title, result.stdout.strip())
        return True
    logger.error("Failed to create issue '%s': %s", title, result.stderr)
    return False


def _build_title(lifecycle: ModelLifecycle) -> str:
    """Build the issue title."""
    status_emoji = {"retiring": "⚠️", "deprecated": "🚫", "shutdown": "🔴"}
    emoji = status_emoji.get(lifecycle.status, "⚠️")
    return f"{emoji} Deprecated model: {lifecycle.model}"


def _build_body(
    lifecycle: ModelLifecycle,
    alerts: list[DeprecationAlert],
) -> str:
    """Build the issue body in Markdown."""
    lines = [
        f"## Model `{lifecycle.model}` is {lifecycle.status}",
        "",
        f"**Provider:** {lifecycle.provider}",
        f"**Status:** {lifecycle.status}",
    ]

    if lifecycle.shutdown_date:
        lines.append(f"**Shutdown date:** {lifecycle.shutdown_date.isoformat()}")
    if lifecycle.replacement:
        lines.append(f"**Recommended replacement:** `{lifecycle.replacement}`")
    if lifecycle.note:
        lines.append(f"**Note:** {lifecycle.note}")

    lines.extend(["", "### Affected files", ""])
    lines.append("| File | Line |")
    lines.append("|------|------|")
    lines.extend(f"| `{alert.match.file}` | {alert.match.line} |" for alert in alerts)

    replacement_text = (
        f"`{lifecycle.replacement}`" if lifecycle.replacement else "a supported model"
    )
    lines.extend(
        [
            "",
            "### Action required",
            f"Migrate from `{lifecycle.model}` to {replacement_text} before the shutdown date.",
            "",
            "---",
            "*This issue was automatically created by the LLM Configuration Scanner.*",
        ]
    )

    return "\n".join(lines)
