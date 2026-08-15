"""Shared BDD step definitions and fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given

from src.deprecations import reload_deprecation_registry


REGISTRE_FIGE = Path(__file__).parent / "data" / "registry_fige.json"


@pytest.fixture
def registre_fige() -> Iterator[None]:
    """Substitue le registre fige au registre de production le temps du test.

    A activer par `pytestmark = pytest.mark.usefixtures("registre_fige")` dans
    tout module dont les assertions portent sur le STATUT d'un modele ou sur le
    fait qu'il soit deprecie. data/registry.json est reecrit tous les quinze
    jours depuis deprecations.info : un scenario qui affirme que `gpt-4.1` est
    encore actif est vrai aujourd'hui et faux le jour ou OpenAI l'annonce, sans
    qu'une seule ligne de code ait bouge.

    test_coherence est la seule exception assumee : sa raison d'etre est
    justement de verifier le registre de production contre les patterns.
    """
    reload_deprecation_registry(REGISTRE_FIGE)
    yield
    reload_deprecation_registry()


@pytest.fixture
def tmp_scan_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for scanning."""
    return tmp_path


@given(
    "a temporary directory with the following files:",
    target_fixture="scan_dir",
)
def given_temp_dir_with_files(
    tmp_scan_dir: Path,
    datatable: list[list[str]],
) -> Path:
    """Create files from a datatable in a temporary directory."""
    headers = datatable[0]
    path_idx = headers.index("path")
    content_idx = headers.index("content")
    for row in datatable[1:]:
        file_path = tmp_scan_dir / row[path_idx]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = row[content_idx].replace("\\n", "\n")
        file_path.write_text(content, encoding="utf-8")
    return tmp_scan_dir


@given(
    "an empty temporary directory",
    target_fixture="scan_dir",
)
def given_empty_dir(tmp_scan_dir: Path) -> Path:
    return tmp_scan_dir
