"""Script de mise a jour du registre de deprecation depuis deprecations.info.

Usage:
    PYTHONPATH=. python -m src.update_registry [--registry-path data/registry.json]
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from pathlib import Path

from src.deprecation_feed import fetch_deprecations
from src.deprecations import (
    _DEFAULT_REGISTRY_PATH,
    DeprecatedModel,
    load_registry,
    merge_registries,
    save_registry,
)
from src.gh import run_gh


logger = logging.getLogger(__name__)

_ISSUE_LABEL = "registry-update"
_GH_TIMEOUT = 30


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Met a jour le registre de deprecation depuis deprecations.info",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=_DEFAULT_REGISTRY_PATH,
        help="Chemin vers le fichier JSON du registre (defaut: data/registry.json)",
    )
    return parser.parse_args(argv)


def _create_feed_failure_issue(error_detail: str) -> None:
    """Cree une issue GitHub signalant l'echec de la recuperation du flux."""
    title = "Echec de la mise a jour du registre de deprecation"
    body = (
        "## Echec de la recuperation du flux deprecations.info\n\n"
        "La mise a jour automatique du registre de deprecation a echoue.\n"
        "Le flux [deprecations.info](https://deprecations.info/) n'a pas pu etre atteint.\n\n"
        f"**Detail de l'erreur :** `{error_detail}`\n\n"
        "### Actions requises\n\n"
        "1. Verifier que le site https://deprecations.info/ est accessible\n"
        "2. Relancer le workflow manuellement depuis l'onglet Actions\n"
        "3. Si le probleme persiste, mettre a jour le registre manuellement "
        "(`data/registry.json`)\n\n"
        "---\n"
        "*Cette issue a ete creee automatiquement par le workflow de mise a jour du registre.*"
    )

    cmd = [
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--label",
        _ISSUE_LABEL,
    ]
    assignees = os.environ.get("LLM_SCAN_ASSIGNEES", "")
    if assignees:
        cmd.extend(["--assignee", assignees])

    try:
        result = run_gh(cmd, timeout=_GH_TIMEOUT)
    except OSError as exc:
        logger.warning("Erreur lors de la creation de l'issue : %s", exc)
        return
    if result is None:
        logger.warning("Erreur lors de la creation de l'issue : delai depasse")
    elif result.returncode == 0:
        logger.info("Issue creee : %s", result.stdout.strip())
    else:
        logger.warning("Impossible de creer l'issue : %s", result.stderr)


_README_MARKER_START = "<!-- REGISTRY_START -->"
_README_MARKER_END = "<!-- REGISTRY_END -->"


def _generate_registry_table(registry: dict[str, DeprecatedModel]) -> str:
    """Genere le tableau Markdown des modeles deprecies pour le README."""
    sorted_entries = sorted(registry.values(), key=lambda dm: (dm.provider, dm.model))
    lines = [
        "| Model | Provider | Status | Shutdown date |",
        "|---|---|---|---|",
    ]
    for dm in sorted_entries:
        shutdown = dm.shutdown_date.isoformat() if dm.shutdown_date else ""
        lines.append(f"| {dm.model} | {dm.provider} | {dm.status} | {shutdown} |")
    return "\n".join(lines)


def update_readme(registry: dict[str, DeprecatedModel], readme_path: Path) -> bool:
    """Met a jour la section auto-generee du README avec le registre actuel.

    Args:
        registry: Le registre de deprecation.
        readme_path: Chemin vers le fichier README.md.

    Returns:
        True si le README a ete modifie, False sinon.
    """
    try:
        content = readme_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Impossible de lire %s", readme_path)
        return False

    table = _generate_registry_table(registry)
    new_section = f"{_README_MARKER_START}\n{table}\n{_README_MARKER_END}"

    pattern = re.compile(
        rf"{re.escape(_README_MARKER_START)}.*?{re.escape(_README_MARKER_END)}",
        re.DOTALL,
    )

    if not pattern.search(content):
        logger.warning("Marqueurs README introuvables dans %s", readme_path)
        return False

    new_content = pattern.sub(new_section, content)
    if new_content == content:
        return False

    readme_path.write_text(new_content, encoding="utf-8")
    logger.info("README mis a jour dans %s", readme_path)
    return True


def update_registry(registry_path: Path) -> int:
    """Recupere le flux, fusionne avec le registre existant et sauvegarde.

    Args:
        registry_path: Chemin vers le fichier JSON du registre.

    Returns:
        Nombre d'entrees du flux traitees.
    """
    current = load_registry(registry_path)
    logger.info("Charge %d entrees depuis %s", len(current), registry_path)

    feed = fetch_deprecations()
    if not feed:
        logger.info("Le flux n'a retourne aucune donnee, registre inchange")
        _create_feed_failure_issue("Le flux n'a retourne aucune donnee")
        return 0

    merged = merge_registries(current, feed)
    changes = len(merged) - len(current)
    logger.info(
        "Fusion : %d existants + %d flux = %d total (%+d)",
        len(current),
        len(feed),
        len(merged),
        changes,
    )

    save_registry(merged, registry_path)
    logger.info("Registre sauvegarde dans %s", registry_path)

    return len(feed)


def main(argv: list[str] | None = None) -> None:
    """Point d'entree du script de mise a jour."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    update_registry(args.registry_path)


if __name__ == "__main__":
    main()
