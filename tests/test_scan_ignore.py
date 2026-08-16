"""BDD step definitions for repository-declared scan exclusions."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from src.models import ScanResult
from src.scan_ignore import IGNORE_FILENAME, ScanIgnore, parse_inline_patterns, parse_patterns
from src.scanner import scan_directory


scenarios("features/scan_ignore.feature")


@given("the exclusion file is a directory")
def given_unreadable_ignore_file(scan_dir: Path) -> None:
    """Rendre le fichier d'exclusion illisible sans le supprimer."""
    (scan_dir / IGNORE_FILENAME).mkdir(parents=True, exist_ok=True)


@given(
    parsers.cfparse('the exclusion patterns "{patterns}"'),
    target_fixture="exclusions",
)
def given_patterns(patterns: str) -> ScanIgnore:
    return ScanIgnore(patterns=tuple(parse_inline_patterns(patterns)))


@when(
    parsers.cfparse('I scan the directory for repo "{repo_name}"'),
    target_fixture="scan_result",
)
def when_scan(scan_dir: Path, repo_name: str) -> ScanResult:
    return scan_directory(scan_dir, repo_name)


@when(
    parsers.cfparse('I scan the directory for repo "{repo_name}" excluding "{patterns}"'),
    target_fixture="scan_result",
)
def when_scan_excluding(scan_dir: Path, repo_name: str, patterns: str) -> ScanResult:
    return scan_directory(
        scan_dir,
        repo_name,
        extra_ignore_patterns=parse_inline_patterns(patterns),
    )


@then(parsers.cfparse("I should find {count:d} scan matches"))
def then_match_count(scan_result: ScanResult, count: int) -> None:
    assert scan_result.match_count == count, (
        f"Expected {count} matches, got {scan_result.match_count}: {scan_result.matches}"
    )


@then(parsers.cfparse('the results should contain model "{model}"'))
def then_contains_model(scan_result: ScanResult, model: str) -> None:
    models = [m.model for m in scan_result.matches]
    assert model in models, f"Expected model '{model}' in {models}"


@then(parsers.cfparse('the path "{path}" should be {verdict}'))
def then_path_verdict(exclusions: ScanIgnore, path: str, verdict: str) -> None:
    attendu = verdict == "excluded"
    assert exclusions.matches(path) is attendu, (
        f"Pattern(s) {exclusions.patterns} on '{path}': expected {verdict}"
    )


def test_parse_patterns_ignores_comments_and_blanks():
    contenu = "# un commentaire\n\n  seed.py  \nfixtures/\n\t# encore un\n"
    assert parse_patterns(contenu) == ["seed.py", "fixtures/"]


def test_parse_inline_patterns_accepts_commas_and_newlines():
    assert parse_inline_patterns("a.py, b.py\nc/*.md") == ["a.py", "b.py", "c/*.md"]


def test_empty_ignore_is_falsy():
    assert not ScanIgnore()
    assert ScanIgnore(patterns=("seed.py",))


def test_empty_ignore_excludes_nothing():
    """Sans motif, aucun chemin ne doit etre ecarte.

    C'est le cas de tous les depots qui ne declarent rien : si `matches`
    repondait vrai pour un chemin quelconque, le scanner se tairait partout
    sans qu'aucun depot ait demande quoi que ce soit.
    """
    vide = ScanIgnore()
    assert not vide.matches("src/app.py")
    assert not vide.matches("")


def test_ignore_file_itself_is_never_scanned(tmp_path: Path):
    """Le fichier d'exclusion cite des chemins, jamais des modeles.

    Il n'a pas d'extension scannable, mais rien ne le dit explicitement : ce
    test fige la garantie, pour qu'ajouter l'extension vide a la liste des
    fichiers scannables ne transforme pas la liste d'exclusions en source de
    faux positifs.
    """
    (tmp_path / IGNORE_FILENAME).write_text("# model = gpt-4o\n", encoding="utf-8")
    resultat = scan_directory(tmp_path, "test-repo")
    assert resultat.match_count == 0
