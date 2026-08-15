"""Appel de la CLI `gh`, avec la meme politique d'echec partout.

Six appels a `gh` repetaient les memes quatre options de `subprocess.run` et le
meme `except TimeoutExpired`. La divergence guettait : un appel oubliant
`check=False` leve une exception la ou les cinq autres renvoient un code, et un
appel sans `timeout` bloque un runner indefiniment.

Le message d'echec, lui, reste chez l'appelant : seul lui sait si un depot
injoignable est fatal ou juste a signaler.
"""

from __future__ import annotations

import subprocess


DEFAULT_TIMEOUT_SECONDS = 30


def run_gh(
    args: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str] | None:
    """Execute `gh <args>` et renvoie le resultat, ou None si la commande expire.

    Ne leve jamais : un code de retour non nul arrive dans `returncode`, une
    expiration se traduit par None. L'appelant decide de la gravite.
    """
    try:
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
