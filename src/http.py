"""Requetes HTTP sortantes, avec la meme politique d'echec partout.

Trois modules appelaient urllib directement : le flux de deprecations, le
webhook CRM et le rapport Slack. Chacun avait sa liste d'exceptions a
rattraper, et elles n'etaient pas equivalentes.

L'ecart le plus couteux portait sur les codes d'erreur HTTP. `urlopen` ne
renvoie pas une reponse pour un 4xx ou un 5xx : il leve `HTTPError`. Le
webhook rattrapait cette exception avec les pannes reseau, puis testait plus
bas `if status == 403` sur une variable qui, a cet endroit, ne pouvait valoir
qu'un code 2xx. Le message d'aide sur le jeton manquant -- la raison meme pour
laquelle le module distingue l'URL du secret -- ne s'est donc jamais affiche.

`Reponse` rend la distinction explicite : un code HTTP est une reponse du
serveur, `status=None` est une absence de reponse.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Reponse:
    """Issue d'une requete sortante.

    Attributes:
        status: Le code HTTP renvoye, ou None si rien n'est revenu du tout
            (panne reseau, delai depasse, URL invalide).
        body: Le corps de la reponse, y compris celui d'une erreur HTTP.
        erreur: Description lisible de l'echec, vide en cas de succes.
    """

    status: int | None
    body: str
    erreur: str = ""

    @property
    def ok(self) -> bool:
        """Vrai pour un code 2xx."""
        return self.status is not None and 200 <= self.status < 300


def request_json(
    url: str,
    *,
    timeout: int,
    payload: object | None = None,
    token: str = "",
    user_agent: str = "",
) -> Reponse:
    """Emet une requete et renvoie son issue. Ne leve jamais.

    Un `payload` non nul est serialise en JSON et bascule la requete en POST.

    Args:
        url: L'URL a joindre.
        timeout: Delai maximal, en secondes.
        payload: Corps a serialiser en JSON, ou None pour un GET.
        token: Jeton porteur, ajoute en `Authorization` s'il est fourni.
        user_agent: En-tete `User-Agent`, ajoute s'il est fourni.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None

    headers = {}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if user_agent:
        headers["User-Agent"] = user_agent

    request = Request(url, data=data, headers=headers)  # noqa: S310 - URL de configuration, jamais saisie

    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return Reponse(status=response.status, body=response.read().decode(errors="replace"))
    except HTTPError as exc:
        # A rattraper avant URLError, dont HTTPError herite.
        return Reponse(
            status=exc.code,
            body=exc.read().decode(errors="replace"),
            erreur=f"HTTP {exc.code}",
        )
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        return Reponse(status=None, body="", erreur=str(exc))
