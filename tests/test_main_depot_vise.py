"""Le depot vise par les appels `gh` est explicite, jamais deduit du cwd.

Corollaire manquant du passage a `working-directory: ${{ github.action_path }}`
(voir tests/test_action_manifest.py). Depuis ce changement, l'action ne
s'execute plus depuis le depot analyse : `gh` n'a donc plus de depot a deduire
du repertoire courant. Sans cible explicite, `_ensure_label`, `_issue_exists` et
`_create_issue` echouent des qu'un modele deprecie est trouve, `issues_failed`
passe a 1, et le scan sort en 1 -- ce qui rougit la CI de tout depot de
l'organisation portant une reference deprecie.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.main import main


def test_main_vise_explicitement_le_depot_analyse(tmp_path: Path) -> None:
    """`main` transmet `target_repo` au createur d'issues."""
    (tmp_path / "config.py").write_text('MODEL = "gpt-4o"\n', encoding="utf-8")

    with patch("src.main.create_issues", return_value=(0, 0)) as create_issues:
        main(
            [
                "--repo-name",
                "Baseline-quebec/depot-analyse",
                "--scan-path",
                str(tmp_path),
            ]
        )

    assert create_issues.called, "le createur d'issues doit etre appele"
    kwargs = create_issues.call_args.kwargs
    assert kwargs.get("target_repo") == "Baseline-quebec/depot-analyse", (
        "main doit passer target_repo : sans lui, gh deduit le depot du "
        "repertoire courant, qui est celui de l'action et non celui analyse."
    )
