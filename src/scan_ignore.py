"""Exclusions de scan declarees par le depot analyse.

Le scanner raisonne sur des chaines de caracteres, pas sur du sens : il ne fait
pas la difference entre `model = "o4-mini"` et une phrase de prose qui cite
`o4-mini`. Certains fichiers sont de la donnee, pas de la configuration, et
aucune heuristique generique ne les distinguera de facon fiable.

Cas reel : `_articles_seed.py` dans baseline-automation contient les resumes
d'articles d'une revue de veille en IA. L'un d'eux rapporte l'annonce du retrait
de GPT-4o par OpenAI et cite `o4-mini` dans sa phrase. Le scanner a ouvert une
issue de depreciation sur un depot dont tout le code tourne deja sur Anthropic,
et l'aurait rouverte a chaque passage.

Le depot analyse declare donc lui-meme ce qui n'est pas de la configuration,
dans un fichier `.llm-scan-ignore`. C'est une decision explicite, versionnee et
relisible, plutot qu'une heuristique qui deciderait a sa place.

Ce fichier est lu a la racine du depot ET dans n'importe quel sous-dossier, ou
ses motifs ne valent que pour ce sous-arbre, comme un `.gitignore`. Sans cela,
la declaration est perdue des que l'arborescence bouge. Cas reel du 2026-08-18
dans Ventes : la PR #154 a remonte la racine du depot d'un niveau, le
`.llm-scan-ignore` qui excluait tout s'est retrouve dans `ODS/`, et les cinq
issues #155 a #159 sont revenues sur les memes offres de service.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath


logger = logging.getLogger(__name__)

IGNORE_FILENAME = ".llm-scan-ignore"

COMMENT_PREFIX = "#"


@dataclass(frozen=True)
class SubtreeIgnore:
    """Motifs declares dans un sous-dossier, valables pour ce sous-arbre seul.

    `base` est le chemin du dossier qui porte le fichier, relatif a la racine du
    scan. Les motifs sont compares au chemin **relatif a ce dossier** : un
    fichier d'exclusion parle de ce qui l'entoure, pas de l'arborescence
    complete au-dessus de lui, et il reste donc valide quand le dossier est
    deplace.
    """

    base: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class ScanIgnore:
    """Ensemble de motifs d'exclusion applique aux chemins scannes."""

    patterns: tuple[str, ...] = ()
    subtrees: tuple[SubtreeIgnore, ...] = ()

    def __bool__(self) -> bool:
        """Vrai si au moins un motif est defini."""
        return bool(self.patterns) or any(sous.patterns for sous in self.subtrees)

    def with_subtree(self, base: str, patterns: Iterable[str]) -> ScanIgnore:
        """Retourne les memes exclusions, augmentees de celles d'un sous-dossier."""
        motifs = tuple(patterns)
        if not motifs:
            return self
        return ScanIgnore(
            patterns=self.patterns,
            subtrees=(*self.subtrees, SubtreeIgnore(base=base, patterns=motifs)),
        )

    def matches(self, relative_path: str) -> bool:
        """Vrai si le chemin, ou l'un de ses dossiers parents, est exclu.

        Le chemin est relatif a la racine scannee et compare en separateurs
        POSIX, pour que les motifs ecrits une fois valent sur les trois systemes.

        Args:
            relative_path: Chemin relatif a la racine du scan.

        Returns:
            True si un motif couvre ce chemin.
        """
        chemin_normalise = relative_path.replace("\\", "/")
        if not self.patterns:
            return self._subtree_matches(chemin_normalise)

        chemin = PurePosixPath(chemin_normalise)
        # Exclure un dossier doit exclure tout ce qu'il contient : on teste le
        # chemin lui-meme puis chacun de ses ancetres, sans quoi `docs/` ne
        # couvrirait pas `docs/veille/articles.py`.
        candidats = [chemin.as_posix()]
        candidats.extend(
            parent.as_posix() for parent in chemin.parents if parent.as_posix() != "."
        )

        if any(
            _motif_couvre(motif, candidat) for motif in self.patterns for candidat in candidats
        ):
            return True

        return self._subtree_matches(chemin_normalise)

    def _subtree_matches(self, relative_path: str) -> bool:
        """Vrai si un fichier d'exclusion d'un sous-dossier couvre ce chemin."""
        for sous in self.subtrees:
            prefixe = f"{sous.base}/"
            if not relative_path.startswith(prefixe):
                continue
            interne = ScanIgnore(patterns=sous.patterns)
            if interne.matches(relative_path[len(prefixe) :]):
                return True
        return False


def _motif_couvre(motif: str, candidat: str) -> bool:
    """Vrai si un motif couvre un chemin candidat."""
    # Le `/` final est la facon usuelle de dire « ce dossier » ; le retirer
    # laisse la comparaison porter sur le chemin du dossier lui-meme.
    motif = motif.rstrip("/")
    if not motif:
        return False

    if fnmatch(candidat, motif):
        return True

    # Un motif sans separateur vise un nom de fichier ou de dossier, a
    # n'importe quelle profondeur : `_articles_seed.py` doit s'ecrire tel quel,
    # sans que l'auteur ait a connaitre le chemin complet.
    return "/" not in motif and fnmatch(PurePosixPath(candidat).name, motif)


def parse_patterns(contenu: str) -> list[str]:
    """Extraire les motifs d'un contenu de fichier d'exclusion.

    Les lignes vides et les commentaires (`#`) sont ignores, les espaces de
    bordure retires.

    Args:
        contenu: Contenu brut du fichier.

    Returns:
        Liste des motifs, dans l'ordre de declaration.
    """
    motifs: list[str] = []
    for ligne in contenu.splitlines():
        nettoyee = ligne.strip()
        if not nettoyee or nettoyee.startswith(COMMENT_PREFIX):
            continue
        motifs.append(nettoyee)
    return motifs


def parse_inline_patterns(valeur: str) -> list[str]:
    """Extraire les motifs passes en ligne de commande ou par l'action.

    Accepte les separateurs virgule et saut de ligne, pour qu'un `with:` YAML
    sur plusieurs lignes et un `--exclude-paths a,b` donnent le meme resultat.

    Args:
        valeur: Motifs concatenes.

    Returns:
        Liste des motifs, dans l'ordre de declaration.
    """
    motifs: list[str] = []
    for fragment in valeur.replace("\n", ",").split(","):
        nettoye = fragment.strip()
        if nettoye and not nettoye.startswith(COMMENT_PREFIX):
            motifs.append(nettoye)
    return motifs


def read_ignore_file(directory: Path) -> list[str]:
    """Lire les motifs du `.llm-scan-ignore` d'un dossier, s'il en porte un.

    Args:
        directory: Dossier susceptible de contenir le fichier.

    Returns:
        Les motifs declares, ou une liste vide si le fichier est absent ou
        illisible : absent est le cas courant, illisible est un accident, et ni
        l'un ni l'autre ne doit empecher le scan de tourner.
    """
    try:
        contenu = (directory / IGNORE_FILENAME).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return parse_patterns(contenu)


def load_ignore(root: Path, extra_patterns: Iterable[str] = ()) -> ScanIgnore:
    """Charger les exclusions applicables a une racine de scan.

    Fusionne le `.llm-scan-ignore` du depot analyse, s'il existe, avec les
    motifs fournis par l'appelant. Le fichier est lu depuis le depot scanne :
    un balayage d'organisation respecte donc les exclusions de chaque depot sans
    configuration centrale.

    Args:
        root: Racine du scan.
        extra_patterns: Motifs supplementaires, par exemple ceux de l'action.

    Returns:
        Les exclusions a appliquer.
    """
    motifs: list[str] = read_ignore_file(root)
    motifs.extend(motif for motif in extra_patterns if motif)

    if motifs:
        logger.info("Exclusions de scan actives : %s", ", ".join(motifs))

    return ScanIgnore(patterns=tuple(motifs))
