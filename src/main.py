"""CLI entry point for the LLM configuration scanner."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from src.deprecations import check_deprecation
from src.issue_reporter import DeprecationAlert, create_issues
from src.scanner import scan_directory


if TYPE_CHECKING:
    from src.models import ScanMatch


logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan a repository for LLM model references and flag deprecated models",
    )
    parser.add_argument(
        "--repo-name",
        required=True,
        help="Name of the repository being scanned",
    )
    parser.add_argument(
        "--scan-path",
        default=".",
        help="Path to the repository root",
    )
    parser.add_argument(
        "--assignees",
        default="",
        help="Comma-separated GitHub usernames to assign deprecation issues",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan only, do not create issues",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = parse_args(argv)
    scan_path = Path(args.scan_path).resolve()

    if not scan_path.is_dir():
        logger.error("Scan path does not exist: %s", scan_path)
        sys.exit(1)

    # Step 1: Scan for model references
    result = scan_directory(scan_path, args.repo_name)
    logger.info("Found %d model references in %s", result.match_count, args.repo_name)

    # Step 2: Check for deprecated models
    alerts = _find_deprecated(result.matches)
    logger.info("Found %d deprecated model references", len(alerts))

    # Step 3: Create issues for deprecated models
    assignees = (
        [a.strip() for a in args.assignees.split(",") if a.strip()] if args.assignees else None
    )
    issues_created = create_issues(alerts, assignees=assignees, dry_run=args.dry_run)

    # Fail if deprecated models were found but no issues could be created
    if alerts and not args.dry_run and issues_created == 0:
        logger.error(
            "Found %d deprecated models but failed to create any issues. "
            "Check that issues are enabled on this repository.",
            len(alerts),
        )
        sys.exit(1)

    # Step 4: Output summary
    _print_summary(result.matches, alerts)

    # Step 5: Set GitHub Actions outputs
    deprecated_summary = _build_deprecated_summary(alerts)
    _set_github_output("match-count", str(result.match_count))
    _set_github_output("deprecated-count", str(len(alerts)))
    _set_github_output("issues-created", str(issues_created))
    _set_github_output("deprecated-summary", json.dumps(deprecated_summary))


def _find_deprecated(matches: list[ScanMatch]) -> list[DeprecationAlert]:
    """Check each LLM match against the deprecation registry."""
    alerts: list[DeprecationAlert] = []
    for match in matches:
        lifecycle = check_deprecation(match.model)
        if lifecycle is not None:
            alerts.append(DeprecationAlert(match=match, lifecycle=lifecycle))
    return alerts


def _build_deprecated_summary(alerts: list[DeprecationAlert]) -> list[dict[str, str]]:
    """Build a JSON-serializable summary of deprecated models (deduplicated)."""
    seen: set[str] = set()
    summary: list[dict[str, str]] = []
    for alert in alerts:
        if alert.lifecycle.model in seen:
            continue
        seen.add(alert.lifecycle.model)
        entry: dict[str, str] = {
            "model": alert.lifecycle.model,
            "provider": alert.lifecycle.provider,
            "status": alert.lifecycle.status,
        }
        if alert.lifecycle.shutdown_date:
            entry["shutdown_date"] = alert.lifecycle.shutdown_date.isoformat()
        summary.append(entry)
    return summary


def _print_summary(matches: list[ScanMatch], alerts: list[DeprecationAlert]) -> None:
    """Print a human-readable summary to stdout."""
    logger.info("=" * 60)
    logger.info("LLM Configuration Scanner Results")
    logger.info("=" * 60)
    logger.info("Total references found: %d", len(matches))
    logger.info("Deprecated models found: %d", len(alerts))

    if alerts:
        logger.info("─" * 40)
        logger.info("Deprecated models:")
        seen: set[str] = set()
        for alert in alerts:
            if alert.lifecycle.model in seen:
                continue
            seen.add(alert.lifecycle.model)
            lc = alert.lifecycle
            shutdown = f" (shutdown: {lc.shutdown_date})" if lc.shutdown_date else ""
            logger.info("  - %s [%s]%s", lc.model, lc.status, shutdown)


def _set_github_output(name: str, value: str) -> None:
    """Set a GitHub Actions output variable using the delimiter format."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    try:
        with Path(github_output).open("a") as f:
            # Use delimiter format to prevent multiline injection
            f.write(f"{name}<<EOF\n{value}\nEOF\n")
    except OSError as exc:
        logger.warning("Could not write GitHub output '%s': %s", name, exc)


if __name__ == "__main__":
    main()
