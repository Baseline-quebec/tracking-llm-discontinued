"""File scanner that walks a directory tree and detects LLM model references."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.models import ScanMatch, ScanResult
from src.patterns import find_matches_in_line
from src.scan_ignore import ScanIgnore, load_ignore, read_ignore_file


if TYPE_CHECKING:
    from collections.abc import Iterable


logger = logging.getLogger(__name__)

# Directories to skip during scanning
# Au-dela, une ligne est du code genere, pas ecrit. Une declaration de modele
# reelle tient tres largement en dessous : la plus longue rencontree dans les
# depots Baseline fait environ 120 caracteres.
MAX_LINE_LENGTH = 500

EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "bower_components",
        "__pycache__",
        "venv",
        ".venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".eggs",
    }
)

# Un journal des changements raconte ce qui a change, pas ce qui tourne.
# « update response llm to gpt-5-chat-latest (#25) » date une bascule ; le
# passage suivant ajoutera une ligne, et les deux resteront vraies. Une entree
# de journal ne se reecrit pas : corrigee apres coup, elle ne sert plus a
# reconstituer l'historique. La signaler revient donc a demander une correction
# qu'il ne faut pas faire.
#
# Le 2026-08-16, six depots de l'organisation ont ouvert une issue sur leur seul
# CHANGELOG : yvan, noa-westwood, sfppn-maintenance-assistee, cmac-monorepo,
# metal-marquis-monorepo et librairies-martin-chatbot. Chacun aurait du declarer
# la meme exclusion ; c'est le signe que la regle appartient au scanner.
#
# La comparaison porte sur le nom sans extension, en majuscules : CHANGELOG.md,
# CHANGELOG.rst, CHANGES.txt, HISTORY.md, RELEASES.md.
EXCLUDED_STEMS: frozenset[str] = frozenset(
    {
        "CHANGELOG",
        "CHANGES",
        "HISTORY",
        "NEWS",
        "RELEASES",
        "RELEASE-NOTES",
        "RELEASE_NOTES",
    }
)

# Une suite de tests n'est pas ce qui tourne. Un modele fixe dans une fixture
# sert a faire passer un test, il n'est appele par aucun service, et le migrer
# ne change rien a ce qui repond en production. Un test qui epingle vraiment un
# modele arrete se signale d'ailleurs tout seul : la suite passe au rouge, ce
# qui est un signal plus sur qu'une issue ouverte a cote.
#
# Le 2026-08-18, trois depots de l'organisation avaient une issue ouverte sur
# leur seul `tests/conftest.py` : cmac-monorepo, metal-marquis-monorepo et
# tourisme-monteregie-chatbot. Trois depots qui declareraient la meme
# exclusion : la regle appartient au scanner.
#
# Un dossier de tests n'est pas parcouru du tout ; hors de ces dossiers, c'est
# le nom du fichier qui tranche.
EXCLUDED_TEST_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "test",
        "__tests__",
        "__mocks__",
        "testdata",
    }
)

# Conventions de nommage des fichiers de test, dans les langages scannes :
# `conftest.py`, `test_x.py`, `x_test.py`, `x.test.ts`, `x.spec.js`, `x_test.go`.
_NOMS_DE_TEST: frozenset[str] = frozenset({"conftest.py"})
_SUFFIXES_DE_TEST: tuple[str, ...] = (".test", ".spec")

# File extensions to scan
SCANNABLE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".md",
        ".txt",
        ".dockerfile",
        ".tf",
        ".hcl",
    }
)

# Files to scan regardless of extension
SCANNABLE_FILENAMES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Makefile",
        ".env",
        ".env.example",
        ".env.local",
        ".env.production",
    }
)

# Max file size to scan (1 MB)
MAX_FILE_SIZE: int = 1_048_576


# Extensions ou une ligne entierement commentee est du code desactive, donc rien
# qui s'execute. `.md` et `.txt` en sont volontairement absents : `#` y ouvre un
# titre, pas un commentaire, et « # Modeles evalues : gpt-4o » est de la prose
# qu'on veut continuer de voir.
_MARQUEURS_COMMENTAIRE: dict[str, tuple[str, ...]] = {
    ".py": ("#",),
    ".sh": ("#",),
    ".yaml": ("#",),
    ".yml": ("#",),
    ".toml": ("#",),
    ".cfg": ("#", ";"),
    ".ini": ("#", ";"),
    ".env": ("#",),
    ".tf": ("#", "//"),
    ".hcl": ("#", "//"),
    ".js": ("//",),
    ".ts": ("//",),
    ".jsx": ("//",),
    ".tsx": ("//",),
}

# Markdown marque lui-meme ce qui est du code : les clotures ``` ou ~~~, et les
# backticks au fil du texte. Hors de ces marques, un nom de modele est cite dans
# une phrase ; il n'y est pas declare.
#
# Le 2026-08-18, l'issue #77 d'agents-support listait trois fichiers pour
# `gpt-4o`. Un seul le configurait (`cli.py`). Les deux autres en parlaient :
# une fiche client resumant les technologies d'un mandat livre en 2024
# (« OpenAI ChatGPT (GPT-4o / GPT-4o-mini), embeddings OpenAI »), et une etude
# de cas racontant une bascule (« Le CHANGELOG de la version v0.4.0 porte la
# ligne "switch to gpt-4o" »). Ni l'une ni l'autre ne se migre : corriger ce
# texte reecrirait un compte rendu.
#
# Une configuration reellement documentee reste vue, parce qu'on l'ecrit en
# code : `MODEL="gpt-4o"` au fil d'une phrase, ou un bloc cloture d'exemple.
# `.txt` reste hors de cette regle, faute d'une convention qui y separe le code
# de la prose ; un fichier de notes se declare dans `.llm-scan-ignore`.
_EXTENSIONS_PROSE: frozenset[str] = frozenset({".md"})

# Une cloture de bloc de code : au plus trois espaces d'indentation, puis au
# moins trois backticks ou tildes (CommonMark).
_CLOTURE_BLOC: re.Pattern[str] = re.compile(r"^ {0,3}(?P<marque>`{3,}|~{3,})")

# Un span de code au fil du texte : n backticks, du contenu, n backticks.
_SPAN_CODE: re.Pattern[str] = re.compile(r"(`+)(?P<code>[^`]+)\1")


def _est_fichier_de_test(path: Path) -> bool:
    """Vrai si le nom du fichier suit une convention de test.

    Couvre les fichiers de test qui vivent a cote du code qu'ils testent, hors
    d'un dossier `tests/` : `conftest.py`, `test_extraction.py`,
    `pricing_test.py`, `VariantsPanel.test.tsx`, `agent.spec.ts`,
    `handler_test.go`.
    """
    if path.name in _NOMS_DE_TEST:
        return True
    tige = path.stem.lower()
    if tige.startswith("test_") or tige.endswith("_test"):
        return True
    return Path(tige).suffix in _SUFFIXES_DE_TEST


def _should_scan_file(path: Path) -> bool:
    """Determine if a file should be scanned based on extension and name."""
    if path.stem.upper() in EXCLUDED_STEMS:
        return False
    if _est_fichier_de_test(path):
        return False
    if path.name in SCANNABLE_FILENAMES:
        return True
    return path.suffix.lower() in SCANNABLE_EXTENSIONS


def _est_ligne_commentee(ligne: str, marqueurs: tuple[str, ...]) -> bool:
    """Vrai si la ligne entiere est un commentaire, dans un langage qui en a.

    Seule une ligne dont le PREMIER caractere non blanc ouvre un commentaire est
    ecartee. Un commentaire de fin de ligne ne l'est pas : dans
    `model = "gpt-4o"  # a bumper`, la configuration est bien active.

    Ce que ce filtre evite : une declaration mise en commentaire est du code
    desactive, et le scanner la presentait comme un modele en service. Cas reel
    du 2026-08-16 dans agents-support, ou un bloc commente contenant
    `anthropic.claude-3-sonnet-20240229-v1:0` a ouvert l'issue la plus alarmante
    de l'organisation -- un modele arrete depuis treize mois -- alors que rien
    ne l'appelait.
    """
    return ligne.lstrip().startswith(marqueurs)


def _masquer_hors_code(ligne: str) -> str:
    """Ne laisse subsister d'une ligne de prose que le contenu ecrit en code.

    Le masquage remplace le reste par des espaces, donc les positions sont
    conservees : la detection de contexte raisonne sur les caracteres voisins,
    et un mot-cle de prose ne doit pas valider un nom de modele qui se trouve
    dans un span de code trois mots plus loin.
    """
    masquee = [" "] * len(ligne)
    for span in _SPAN_CODE.finditer(ligne):
        debut, fin = span.span("code")
        masquee[debut:fin] = ligne[debut:fin]
    return "".join(masquee)


def _reduire_markdown_au_code(lignes: list[str]) -> list[str]:
    """Ne garde de chaque ligne markdown que ce que l'auteur a ecrit en code.

    Le contenu d'un bloc cloture est rendu tel quel ; ailleurs, seuls les spans
    entre backticks subsistent. Le nombre de lignes ne change pas, pour que le
    numero rapporte reste celui du fichier.

    Un bloc ouvert et jamais referme court jusqu'a la fin du fichier, comme le
    veut CommonMark : mieux vaut lire un exemple de configuration jusqu'au bout
    que de le perdre parce qu'une cloture manque.
    """
    reduites: list[str] = []
    cloture: str | None = None

    for ligne in lignes:
        marque = _CLOTURE_BLOC.match(ligne)
        if cloture is None:
            if marque is not None:
                cloture = marque.group("marque")
                reduites.append("")
            else:
                reduites.append(_masquer_hors_code(ligne))
            continue
        ouverture = marque.group("marque") if marque is not None else ""
        if ouverture.startswith(cloture[0]) and len(ouverture) >= len(cloture):
            cloture = None
            reduites.append("")
        else:
            reduites.append(ligne)

    return reduites


def _should_skip_dir(dirname: str) -> bool:
    """Determine if a directory should be skipped."""
    return (
        dirname in EXCLUDED_DIRS
        or dirname.lower() in EXCLUDED_TEST_DIRS
        or dirname.endswith(".egg-info")
    )


def scan_directory(
    scan_path: Path,
    repo_name: str,
    *,
    extra_ignore_patterns: Iterable[str] = (),
) -> ScanResult:
    """Scan a directory tree for LLM model references.

    Les exclusions declarees par le depot analyse (`.llm-scan-ignore`, a sa
    racine ou dans n'importe quel sous-dossier) sont chargees ici, et non par
    l'appelant : tout point d'entree du scanner les respecte donc, y compris le
    balayage d'organisation qui clone des depots dont il ne connait pas la
    configuration.

    Args:
        scan_path: Root directory to scan.
        repo_name: Name of the repository (used in results).
        extra_ignore_patterns: Motifs d'exclusion supplementaires, fusionnes
            avec ceux du depot.

    Returns:
        ScanResult with deduplicated matches.
    """
    seen: set[tuple[str, str, str]] = set()  # (model, file, match_type) for dedup
    matches: list[ScanMatch] = []

    ignore = load_ignore(scan_path, extra_ignore_patterns)
    files, ignored_paths = _walk_files(scan_path, ignore)

    for file_path in files:
        relative_path = str(file_path.relative_to(scan_path))
        _scan_file(file_path, relative_path, seen, matches)

    # Une exclusion qui n'est pas dite est une exclusion invisible : sans cette
    # trace, un motif trop large ferait taire des pans entiers du depot et le
    # scan sortirait « 0 modele deprecie » avec la meme assurance que s'il
    # avait tout lu. Les chemins sont nommes, pas seulement comptes, parce que
    # c'est le nom qui permet de voir qu'un motif a mordu trop large.
    if ignored_paths:
        logger.info(
            "Excluded from %s by scan exclusions: %s",
            repo_name,
            ", ".join(ignored_paths),
        )

    logger.info("Scanned %s: found %d unique matches", repo_name, len(matches))
    return ScanResult(repo_name=repo_name, matches=matches)


def _walk_files(root: Path, ignore: ScanIgnore | None = None) -> tuple[list[Path], list[str]]:
    """Walk directory tree returning scannable files (iterative).

    Un `.llm-scan-ignore` rencontre dans un sous-dossier est charge en descendant,
    avant que les enfants de ce dossier ne soient examines, et ses motifs ne
    valent que pour ce sous-arbre. Un dossier deja exclu n'est pas ouvert, donc
    un fichier d'exclusion qu'il contiendrait n'a rien a dire de plus.

    Returns:
        Le couple (fichiers a scanner, chemins ecartes par une exclusion). Un
        dossier exclu compte pour un seul chemin, celui du dossier : il n'est
        pas parcouru. Les fichiers ecartes par une regle du scanner lui-meme
        (extension, taille, dossier exclu en dur) ne sont pas listes, ce ne
        sont pas des decisions du depot.
    """
    files: list[Path] = []
    ignored: list[str] = []
    exclusions = ignore or ScanIgnore()

    if not root.is_dir():
        return files, ignored

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        if current != root:
            # Les motifs d'un sous-dossier sont portes par leur prefixe, donc les
            # ajouter aux exclusions communes ne peut pas mordre ailleurs dans
            # l'arborescence.
            base = current.relative_to(root).as_posix()
            motifs = read_ignore_file(current)
            if motifs:
                logger.info("Exclusions declarees dans %s : %s", base, ", ".join(motifs))
                exclusions = exclusions.with_subtree(base, motifs)
        try:
            children = sorted(current.iterdir(), reverse=True)
        except OSError:
            continue
        for item in children:
            relative = item.relative_to(root).as_posix()
            if item.is_dir():
                if _should_skip_dir(item.name):
                    continue
                # Un dossier exclu n'est pas parcouru du tout : inutile de
                # descendre pour rejeter chaque fichier un par un.
                if exclusions.matches(relative):
                    ignored.append(f"{relative}/")
                    continue
                stack.append(item)
            elif (
                item.is_file() and _should_scan_file(item) and item.stat().st_size <= MAX_FILE_SIZE
            ):
                if exclusions.matches(relative):
                    ignored.append(relative)
                    continue
                files.append(item)

    return files, sorted(ignored)


def _is_minified(file_path: Path) -> bool:
    """Vrai si le nom du fichier annonce du contenu minifie ou groupe.

    Complete le garde-fou sur la longueur de ligne : certains bundles gardent
    des sauts de ligne tout en restant du code genere que personne ne modifie.
    """
    nom = file_path.name.lower()
    return ".min." in nom or "-min." in nom or "-min-" in nom or nom.endswith(".bundle.js")


def _scan_file(
    file_path: Path,
    relative_path: str,
    seen: set[tuple[str, str, str]],
    matches: list[ScanMatch],
) -> None:
    """Scan a single file for LLM model references."""
    if _is_minified(file_path):
        return

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        logger.warning("Could not read %s: %s", relative_path, exc)
        return

    extension = file_path.suffix.lower()
    marqueurs = _MARQUEURS_COMMENTAIRE.get(extension, ())

    lignes = content.splitlines()
    if extension in _EXTENSIONS_PROSE:
        lignes = _reduire_markdown_au_code(lignes)

    for line_num, line in enumerate(lignes, start=1):
        if marqueurs and _est_ligne_commentee(line, marqueurs):
            continue
        # Une ligne aussi longue n'est pas du code ecrit par un humain : c'est du
        # minifie ou un bundle. Le probleme n'est pas seulement le bruit, c'est
        # que la detection de contexte raisonne PAR LIGNE. Un fichier minifie
        # tient sur une seule ligne de plusieurs dizaines de milliers de
        # caracteres, donc n'importe quel mot-cle present ailleurs dans le
        # fichier valide le contexte d'un nom de modele court comme `ada`.
        # Cas reel : ext-modelist.js de l'editeur ACE, qui liste ses modes de
        # langage dont Ada, a ouvert une issue dans baseline.quebec.
        if len(line) > MAX_LINE_LENGTH:
            continue
        for provider, model_name, match_type in find_matches_in_line(line):
            dedup_key = (model_name, relative_path, match_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            matches.append(
                ScanMatch(
                    provider=provider,
                    model=model_name,
                    match_type=match_type,
                    file=relative_path,
                    line=line_num,
                )
            )
