"""File scanner that walks a directory tree and detects LLM model references."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from src.models import ScanMatch, ScanResult
from src.patterns import find_matches_in_line


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

# Fichier d'exclusion depose a la racine du depot scanne.
#
# Un depot peut contenir des noms de modeles sans contenir un seul appel de
# modele : offres de service, audits, comptes rendus. Un nom de modele y decrit
# la solution proposee au client ou l'existant audite, jamais une configuration.
# Le scanner ne peut pas trancher depuis le texte ; le depot, lui, le sait, et
# l'ecrit dans ce fichier.
IGNORE_FILE_NAME = ".llm-scan-ignore"


@dataclass(frozen=True)
class IgnoreRule:
    """Une ligne du fichier d'exclusion.

    `negated` porte les lignes prefixees de `!`, qui reinjectent un chemin exclu
    par une regle precedente. C'est ce qui rend exprimable le cas « tout ce
    depot est de la documentation, sauf ce dossier de code ».
    """

    pattern: str
    negated: bool


def _should_scan_file(path: Path) -> bool:
    """Determine if a file should be scanned based on extension and name."""
    if path.name in SCANNABLE_FILENAMES:
        return True
    return path.suffix.lower() in SCANNABLE_EXTENSIONS


def _should_skip_dir(dirname: str) -> bool:
    """Determine if a directory should be skipped."""
    return dirname in EXCLUDED_DIRS or dirname.endswith(".egg-info")


def load_ignore_rules(scan_path: Path) -> list[IgnoreRule]:
    """Lit les regles d'exclusion a la racine du depot scanne.

    Syntaxe reduite de .gitignore : une regle par ligne, `#` en commentaire,
    lignes vides ignorees, `!` pour reinjecter. Un fichier absent ou illisible
    ne donne aucune regle : l'exclusion est une option, pas un prerequis.
    """
    ignore_file = scan_path / IGNORE_FILE_NAME
    try:
        content = ignore_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    rules: list[IgnoreRule] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:].strip() if negated else line
        if pattern:
            rules.append(IgnoreRule(pattern=pattern, negated=negated))

    if rules:
        logger.info("%s: %d regle(s) d'exclusion chargee(s)", IGNORE_FILE_NAME, len(rules))
    return rules


def _rule_matches(relative_path: str, pattern: str) -> bool:
    """Vrai si un chemin relatif POSIX est vise par une regle d'exclusion."""
    target = pattern.rstrip("/")
    if not target:
        return False
    # `docs/` comme `docs` visent aussi tout ce qui se trouve dessous.
    if fnmatchcase(relative_path, target) or fnmatchcase(relative_path, f"{target}/*"):
        return True
    # Une regle sans separateur vise un nom, a n'importe quelle profondeur :
    # `*.md` exclut la documentation partout, `Mandat` exclut chaque dossier qui
    # porte ce nom. Une regle avec separateur reste ancree a la racine.
    if "/" not in target:
        return any(fnmatchcase(part, target) for part in relative_path.split("/"))
    return False


def is_ignored(relative_path: str, rules: list[IgnoreRule]) -> bool:
    """Applique les regles dans l'ordre du fichier ; la derniere qui matche gagne.

    L'ordre compte, comme dans .gitignore : `*` suivi de `!src/` exclut tout le
    depot sauf le code, alors que l'ordre inverse n'exclurait plus rien.
    """
    ignored = False
    for rule in rules:
        if _rule_matches(relative_path, rule.pattern):
            ignored = not rule.negated
    return ignored


def scan_directory(scan_path: Path, repo_name: str) -> ScanResult:
    """Scan a directory tree for LLM model references.

    Args:
        scan_path: Root directory to scan.
        repo_name: Name of the repository (used in results).

    Returns:
        ScanResult with deduplicated matches.
    """
    seen: set[tuple[str, str, str]] = set()  # (model, file, match_type) for dedup
    matches: list[ScanMatch] = []
    rules = load_ignore_rules(scan_path)
    ignored_files = 0

    for file_path in _walk_files(scan_path):
        relative_path = file_path.relative_to(scan_path).as_posix()
        if is_ignored(relative_path, rules):
            ignored_files += 1
            continue
        _scan_file(file_path, relative_path, seen, matches)

    if ignored_files:
        logger.info("%s: %d fichier(s) exclu(s) du scan", IGNORE_FILE_NAME, ignored_files)
    logger.info("Scanned %s: found %d unique matches", repo_name, len(matches))
    return ScanResult(repo_name=repo_name, matches=matches)


def _walk_files(root: Path) -> list[Path]:
    """Walk directory tree returning scannable files (iterative)."""
    files: list[Path] = []

    if not root.is_dir():
        return files

    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), reverse=True)
        except OSError:
            continue
        for item in children:
            if item.is_dir():
                if not _should_skip_dir(item.name):
                    stack.append(item)
            elif (
                item.is_file() and _should_scan_file(item) and item.stat().st_size <= MAX_FILE_SIZE
            ):
                files.append(item)

    return files


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

    for line_num, line in enumerate(content.splitlines(), start=1):
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
