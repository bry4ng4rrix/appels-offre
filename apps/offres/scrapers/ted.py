"""Marches europeens publies au Journal officiel de l'UE (TED).

Source : https://api.ted.europa.eu/v3/notices/search

API publique, sans authentification. Elle n'accepte la recherche qu'en POST :
un GET repond 405.

Cadre juridique le plus favorable du pipeline. La notice legale de TED
(https://ted.europa.eu/en/legal-notice) enonce que les avis publies au
Supplement au Journal officiel « can be freely reused, for commercial or
non-commercial purposes ». Aucune demande d'autorisation n'est requise, ni
pour la collecte ni pour la rediffusion.

Trois particularites verifiees le 24/08/2026 :

1. Les dates de la requete s'ecrivent AAAAMMJJ, sans tirets. Le format ISO
   avec tirets est rejete par un 400 explicite.

2. Le titre vit dans `title-proc` pour les avis recents, dans `notice-title`
   pour les plus anciens -- les deux sous forme de dictionnaires multilingues
   dont la valeur est tantot une chaine, tantot une liste.

3. Le filtre est volontairement restreint a Madagascar. Le CPV 72 (services
   informatiques) donne 2929 avis ouverts a l'echelle de l'UE, majoritairement
   reserves aux entreprises etablies dans l'Union : les inclure noierait le
   pipeline sans benefice.
"""

from datetime import date

from .base import BaseScraper
from .http import post_json
from Offre.sources import (
    TED_API_URL,
    TED_PAYS,
    TED_PAGE_SIZE,
    TED_MAX_PAGES,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {
    "User-Agent": "veille-appels/1.0",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

#: Champs valides, verifies un par un contre l'API.
CHAMPS = [
    "publication-number", "title-proc", "notice-title", "description-lot",
    "buyer-name", "deadline-receipt-request", "classification-cpv",
    "place-of-performance", "publication-date", "links",
]

#: Langues preferees pour les champs multilingues, dans l'ordre.
LANGUES = ("fra", "eng", "fre", "en", "fr")


def texte_multi(valeur) -> str:
    """Extrait une chaine d'un champ multilingue de TED.

    Le format varie : dictionnaire {langue: chaine} ou {langue: [chaine]},
    parfois une simple chaine. On privilegie le francais puis l'anglais, et a
    defaut la premiere langue disponible plutot que de renvoyer vide.
    """
    if not valeur:
        return ""
    if isinstance(valeur, str):
        return valeur.strip()
    if isinstance(valeur, list):
        return texte_multi(valeur[0]) if valeur else ""
    if isinstance(valeur, dict):
        for langue in LANGUES:
            if valeur.get(langue):
                return texte_multi(valeur[langue])
        for v in valeur.values():
            if v:
                return texte_multi(v)
    return ""


def premiere(valeur) -> str:
    """Premiere entree d'un champ liste ("deadline-receipt-request")."""
    if isinstance(valeur, list):
        return str(valeur[0]) if valeur else ""
    return str(valeur or "")


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    numero = brut.get("publication-number") or ""
    # title-proc pour les avis recents, notice-title pour les anciens.
    titre = texte_multi(brut.get("title-proc")) or texte_multi(brut.get("notice-title"))
    description = texte_multi(brut.get("description-lot"))
    echeance = premiere(brut.get("deadline-receipt-request"))[:10]

    cpv = brut.get("classification-cpv") or []
    lieux = brut.get("place-of-performance") or []
    details = []
    if brut.get("publication-date"):
        details.append(f"Publie le {str(brut['publication-date'])[:10]}")
    if cpv:
        details.append("CPV " + ", ".join(sorted(set(cpv))[:5]))
    if lieux:
        details.append("Lieu " + ", ".join(sorted(set(lieux))[:3]))

    return {
        "id": f"ted-{numero}" if numero else "",
        "source": "ted",
        "titre": titre or description[:150] or f"Avis TED {numero}",
        "organisation": texte_multi(brut.get("buyer-name")),
        # Le champ porte des codes ISO-3 ; on affiche Madagascar en clair quand
        # c'est le cas, sinon le code brut, pour que la regle geographique du
        # prompt de tri se declenche.
        "pays": "Madagascar" if "MDG" in lieux else (lieux[0] if lieux else ""),
        "date_limite": echeance,
        "description": (". ".join(details) + ". " if details else "") + description[:1200],
        "lien": f"https://ted.europa.eu/fr/notice/{numero}" if numero else "",
    }


def fetch_page(pays: str, page: int) -> list:
    """Une page d'avis encore ouverts pour un pays d'execution.

    Le format de date exige par l'API est AAAAMMJJ : l'ISO avec tirets est
    rejete par un 400.
    """
    aujourdhui = date.today().strftime("%Y%m%d")
    requete = (f"place-of-performance={pays} AND "
               f"deadline-receipt-request>{aujourdhui}")
    reponse = post_json(TED_API_URL, HEADERS, {
        "query": requete,
        "limit": TED_PAGE_SIZE,
        "page": page,
        "fields": CHAMPS,
    })
    return reponse.get("notices") or []


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus encore ouverts.

    L'API ne renvoyant deja que les avis dont l'echeance est future, aucun
    filtrage supplementaire n'est necessaire ici -- contrairement au FID ou a
    la BAD, ou il faut trier les archives.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for pays in (TED_PAYS or ["MDG"]):
        for page in range(1, TED_MAX_PAGES + 1):
            try:
                bruts = fetch_page(pays, page)
            except Exception as exc:
                print(f"TED : {pays} page {page} en echec ({str(exc)[:70]}).")
                break

            if not bruts:
                break

            neufs_page = 0
            for brut in bruts:
                item = normalize(brut)
                if not item["id"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
                    continue
                vus_ce_run.add(item["id"])
                nouveaux.append(item)
                neufs_page += 1
                if limite is not None and len(nouveaux) >= limite:
                    print(f"TED : plafond premier lancement atteint ({limite} avis).")
                    return nouveaux

            if not complet and neufs_page == 0:
                break

    return nouveaux


class TedScraper(BaseScraper):
    source_key = "ted"
    nom = "TED (Union europeenne)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
