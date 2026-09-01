"""Tests du manifeste action.yml : invariants d'execution de l'action composite.

Ces tests figent des proprietes du manifeste qu'aucun test unitaire ne couvre,
parce qu'elles ne se manifestent qu'a l'execution dans un runner GitHub.
"""

from __future__ import annotations

import re
from pathlib import Path


ACTION_YML = Path(__file__).resolve().parent.parent / "action.yml"


def _bloc_etape_scan() -> str:
    """Renvoie le texte de l'etape "Run LLM scanner" du manifeste."""
    texte = ACTION_YML.read_text(encoding="utf-8")
    debut = texte.index("- name: Run LLM scanner")
    return texte[debut:]


def test_le_scan_s_execute_depuis_le_repertoire_de_l_action() -> None:
    """L'etape de scan doit fixer `working-directory` au repertoire de l'action.

    `python -m src.main` place le repertoire courant en tete de `sys.path`,
    AVANT le `PYTHONPATH` du manifeste. Sans `working-directory`, le repertoire
    courant est le workspace du depot analyse : tout depot ayant son propre
    paquet `src/` (layout src, tres repandu en Python) masque le `src/` de
    l'action et le scan echoue sur « No module named src.main ». L'action etant
    un workflow requis au niveau de l'organisation, cet echec bloque tout merge
    sur les depots concernes.
    """
    bloc = _bloc_etape_scan()
    assert "working-directory: ${{ github.action_path }}" in bloc, (
        "L'etape de scan doit declarer `working-directory: ${{ github.action_path }}`, "
        "sinon le paquet `src/` du depot analyse masque celui de l'action."
    )


def test_le_chemin_de_scan_reste_absolu() -> None:
    """`--scan-path` doit viser le workspace en absolu.

    Corollaire du test precedent : puisque l'action ne s'execute plus depuis le
    depot analyse, un chemin de scan relatif viserait le repertoire de l'action
    et scannerait le scanner lui-meme.
    """
    bloc = _bloc_etape_scan()
    assert re.search(r"SCAN_PATH:\s*\$\{\{\s*github\.workspace\s*\}\}", bloc), (
        "SCAN_PATH doit valoir ${{ github.workspace }} : un chemin relatif "
        "scannerait le repertoire de l'action."
    )
