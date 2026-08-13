"""Organisation-wide sweep for deprecated model references.

The per-repository action only runs on pull requests, so it catches a deprecated
model being *introduced*. It can never catch drift: when a provider deprecates a
model, the registry changes but the repository code does not, no pull request is
opened, and nothing runs. This sweep closes that gap by cloning every repository
in the organisation on a schedule and scanning it against the current registry.

Repositories are cloned shallow into a temporary directory and deleted right
after scanning, so nothing persists on the runner.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from src.deprecations import check_deprecation
from src.issue_reporter import DeprecationAlert, create_issues
from src.jira import create_ticket
from src.scanner import scan_directory


logger = logging.getLogger(__name__)

GH_TIMEOUT_SECONDS = 60
CLONE_TIMEOUT_SECONDS = 300
REPO_LIST_LIMIT = 500


@dataclass(frozen=True)
class Repository:
    """A repository to sweep."""

    name_with_owner: str

    @property
    def name(self) -> str:
        """Return the repository name without its owner."""
        return self.name_with_owner.split("/")[-1]


@dataclass
class SweepResult:
    """Outcome of sweeping a single repository."""

    repository: str
    scanned: bool = False
    deprecated_models: list[str] = field(default_factory=list)
    issues_created: int = 0
    error: str = ""


def list_repositories(org: str, excluded: set[str] | None = None) -> list[Repository]:
    """List the organisation's non-archived, non-fork repositories.

    Archived repositories are excluded on purpose: they cannot receive issues,
    and a deprecated model in code nobody runs is not actionable.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                org,
                "--limit",
                str(REPO_LIST_LIMIT),
                "--no-archived",
                "--source",
                "--json",
                "nameWithOwner,isArchived,hasIssuesEnabled",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.error("Timeout listing repositories for %s", org)
        return []

    if result.returncode != 0:
        logger.error("Failed to list repositories: %s", result.stderr.strip())
        return []

    try:
        payload: list[dict[str, object]] = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Could not parse repository list: %s", result.stdout[:200])
        return []

    excluded = excluded or set()
    repositories: list[Repository] = []
    for entry in payload:
        name = str(entry.get("nameWithOwner", ""))
        if not name or name in excluded or name.split("/")[-1] in excluded:
            continue
        # A repository with issues disabled cannot be alerted; skipping it here
        # avoids a guaranteed failure later and keeps the run green for a
        # condition that is a repository setting, not a code problem.
        if entry.get("hasIssuesEnabled") is False:
            logger.warning("Issues disabled on %s, skipping", name)
            continue
        repositories.append(Repository(name_with_owner=name))
    return repositories


def clone(repository: Repository, destination: Path) -> bool:
    """Shallow-clone a repository. Returns True on success."""
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "clone",
                repository.name_with_owner,
                str(destination),
                "--",
                "--depth",
                "1",
                "--single-branch",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout cloning %s", repository.name_with_owner)
        return False
    if result.returncode != 0:
        logger.warning("Failed to clone %s: %s", repository.name_with_owner, result.stderr.strip())
        return False
    return True


def sweep_repository(
    repository: Repository,
    *,
    assignees: list[str] | None,
    dry_run: bool,
) -> SweepResult:
    """Clone, scan and alert a single repository."""
    outcome = SweepResult(repository=repository.name_with_owner)

    with tempfile.TemporaryDirectory(prefix="sweep-") as workspace:
        destination = Path(workspace) / repository.name
        if not clone(repository, destination):
            outcome.error = "clone failed"
            return outcome

        scan = scan_directory(destination, repository.name_with_owner)
        outcome.scanned = True

        alerts = [
            DeprecationAlert(match=match, lifecycle=lifecycle)
            for match in scan.matches
            if (lifecycle := check_deprecation(match.model)) is not None
        ]
        outcome.deprecated_models = sorted({alert.lifecycle.model for alert in alerts})

        if not alerts:
            return outcome

        created, failed = create_issues(
            alerts,
            assignees=assignees,
            dry_run=dry_run,
            repo_name=repository.name_with_owner,
            target_repo=repository.name_with_owner,
        )
        outcome.issues_created = created
        if failed:
            outcome.error = f"{failed} issue(s) could not be created"

    return outcome


def sweep(
    org: str,
    *,
    assignees: list[str] | None = None,
    dry_run: bool = False,
    excluded: set[str] | None = None,
) -> list[SweepResult]:
    """Sweep every repository of the organisation."""
    repositories = list_repositories(org, excluded)
    logger.info("Sweeping %d repositories in %s", len(repositories), org)

    results: list[SweepResult] = []
    for index, repository in enumerate(repositories, start=1):
        logger.info("[%d/%d] %s", index, len(repositories), repository.name_with_owner)
        results.append(sweep_repository(repository, assignees=assignees, dry_run=dry_run))
    return results


def build_summary(results: list[SweepResult]) -> str:
    """Build the Markdown summary written to the job output."""
    affected = [r for r in results if r.deprecated_models]
    failed = [r for r in results if r.error]

    lines = [
        "## Balayage mensuel des modèles dépréciés",
        "",
        f"- Dépôts analysés : **{sum(1 for r in results if r.scanned)}** sur {len(results)}",
        f"- Dépôts touchés : **{len(affected)}**",
        f"- Issues créées : **{sum(r.issues_created for r in results)}**",
        "",
    ]

    if affected:
        lines += [
            "### Dépôts touchés",
            "",
            "| Dépôt | Modèles dépréciés | Issues |",
            "|---|---|---|",
        ]
        lines += [
            f"| `{r.repository}` | {', '.join(r.deprecated_models)} | {r.issues_created} |"
            for r in sorted(affected, key=lambda r: r.repository)
        ]
        lines.append("")

    if failed:
        lines += ["### Dépôts non analysés", "", "| Dépôt | Raison |", "|---|---|"]
        lines += [
            f"| `{r.repository}` | {r.error} |" for r in sorted(failed, key=lambda r: r.repository)
        ]
        lines.append("")

    if not affected:
        lines.append("Aucun modèle déprécié référencé dans l'organisation.")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True, help="GitHub organisation to sweep")
    parser.add_argument("--assignees", default="", help="Comma-separated GitHub usernames")
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated repositories to skip, by name or owner/name",
    )
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not create issues")
    parser.add_argument("--summary-out", type=Path, help="Write the Markdown summary to this file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Sweep the organisation and report. Always returns 0."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    assignees = [a.strip() for a in args.assignees.split(",") if a.strip()] or None
    excluded = {e.strip() for e in args.exclude.split(",") if e.strip()}

    results = sweep(args.org, assignees=assignees, dry_run=args.dry_run, excluded=excluded)

    # An organisation with zero repositories is not a clean sweep, it is a
    # broken one. The usual cause is a token that is valid but not authorised
    # for the organisation under SAML single sign-on: the GraphQL listing then
    # returns an empty array instead of an error, and the run would otherwise
    # end green having scanned nothing at all.
    if not results:
        logger.error(
            "::error title=Aucun depot::Aucun depot listable dans %s. "
            "Verifier que le jeton est autorise pour l'organisation (SSO SAML).",
            args.org,
        )
        return 1

    summary = build_summary(results)

    print(summary)
    if args.summary_out:
        args.summary_out.write_text(summary + "\n", encoding="utf-8")

    affected = [r for r in results if r.deprecated_models]
    if affected and not args.dry_run:
        create_ticket(summary, len(affected))

    # A failed clone is reported but never fails the run: one unreachable
    # repository must not hide the results of the eighty-one others.
    for result in results:
        if result.error:
            logger.warning("%s: %s", result.repository, result.error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
