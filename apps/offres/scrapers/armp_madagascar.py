"""Avis de marches publics malgaches (ARMP).

Source : http://www.armp.mg/marches_publics/

Autorite de Regulation des Marches Publics de Madagascar. C'est la source la
plus directement exploitable du pipeline : marches nationaux, en francais,
avec une vraie date limite de depot.

Constate le 21/08/2026 :
  - Aucun robots.txt (404), aucune mention legale, aucun copyright. Les avis
    sont publies precisement pour etre lus par les candidats.
  - Tout tient sur UNE page (~800 Ko, 424 avis) : pas de pagination, donc une
    seule requete par execution. Source la moins couteuse du pipeline.
  - Le site ne repond qu'en HTTP, pas en HTTPS. Les donnees sont publiques,
    mais rien ne garantit qu'elles n'ont pas ete alterees en transit.

Structure : un tableau par region, precede de "REGION : NOM (n avis)".
Colonnes : ENTITE (avec Ref), OBJET, DATE ("Du: ... Au: ..."), lien PDF.
"""

import re
from datetime import date
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (
    ARMP_BASE_URL,
    ARMP_OUVERTS_SEULEMENT,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.8",
}


def nettoyer_entite(brut: str) -> tuple:
    """Separe l'organisme de sa reference.

    Le champ arrive sous la forme :
        "MINISTERE DES TRAVAUX PUBLICS ------------- Ref: 039-TR/MTP/PR"
    Les tirets sont un remplissage d'affichage, pas un separateur fiable :
    on decoupe sur "Ref:" puis on retire les tirets residuels.
    """
    brut = (brut or "").strip()
    reference = ""
    m = re.search(r"Ref\s*:\s*(.+)$", brut, re.I)
    if m:
        reference = m.group(1).strip()
        brut = brut[:m.start()]
    organisme = re.sub(r"[-\s]+$", "", brut).strip()
    return organisme, reference


def dates_avis(brut: str) -> tuple:
    """Extrait (publication, echeance) de "Du: 2026-08-20 Au: 2026-09-03".

    Les dates sont deja en ISO : aucune table de mois n'est necessaire ici,
    contrairement a UNjobnet et a la BAD.
    """
    debut = re.search(r"Du\s*:\s*(\d{4}-\d{2}-\d{2})", brut or "")
    fin = re.search(r"Au\s*:\s*(\d{4}-\d{2}-\d{2})", brut or "")
    return (debut.group(1) if debut else "", fin.group(1) if fin else "")


def identifiant(lien: str) -> str:
    """Le numero de dossier du lien PDF sert d'identifiant stable.

    Exemple : .../ASAPC_SUB.php?num_dos=2600092-19CPX001 -> armp-2600092-19CPX001
    """
    if not lien:
        return ""
    num = parse_qs(urlparse(lien).query).get("num_dos", [""])[0].strip()
    return f"armp-{num}" if num else ""


def est_ouvert(echeance: str) -> bool:
    """Vrai si la date limite n'est pas passee.

    Un avis sans echeance lisible est conserve : on ne peut pas affirmer
    qu'il est clos.
    """
    if not echeance:
        return True
    try:
        return date.fromisoformat(echeance) >= date.today()
    except ValueError:
        return True


def fetch_avis() -> list:
    """Recupere et parse la page unique. Renvoie la liste brute des avis."""
    soup = BeautifulSoup(get_html(ARMP_BASE_URL, HEADERS, timeout=90), "html.parser")

    avis = []
    for table in soup.find_all("table"):
        # Le nom de region precede le tableau ("REGION : ANALAMANGA (40 avis)").
        precedent = table.find_previous(string=re.compile(r"REGION\s*:", re.I))
        region = ""
        if precedent:
            m = re.search(r"REGION\s*:\s*([^(]+)", str(precedent), re.I)
            if m:
                region = m.group(1).strip()

        for ligne in table.find_all("tr")[1:]:      # [0] = en-tetes
            cellules = ligne.find_all("td")
            if len(cellules) < 4:
                continue
            lien_el = cellules[3].find("a")
            avis.append({
                "entite": cellules[0].get_text(" ", strip=True),
                "objet": cellules[1].get_text(" ", strip=True),
                "dates": cellules[2].get_text(" ", strip=True),
                "lien": lien_el.get("href", "") if lien_el else "",
                "region": region,
            })
    return avis


def normalize(brut: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    organisme, reference = nettoyer_entite(brut["entite"])
    publie, echeance = dates_avis(brut["dates"])

    details = [f"Région : {brut['region']}" if brut["region"] else "",
               f"Référence : {reference}" if reference else "",
               f"Publié le {publie}" if publie else ""]

    return {
        "id": identifiant(brut["lien"]),
        "source": "armp",
        "titre": brut["objet"],
        "organisation": organisme,
        # "Madagascar" et non la region : c'est ce que la regle geographique
        # de TRIAGE_PROMPT reconnait. La region va dans la description.
        "pays": "Madagascar",
        "date_limite": echeance,
        "description": ". ".join(d for d in details if d),
        "lien": brut["lien"],
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus.

    Pas de pagination a gerer : la page porte l'integralite des avis en cours.
    Le mode complet ne change donc rien ici, sinon l'absence de plafond.
    """
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    nouveaux = []
    vus_ce_run = set()
    ignores_clos = 0

    for brut in fetch_avis():
        item = normalize(brut)
        if not item["id"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
            continue
        if ARMP_OUVERTS_SEULEMENT and not est_ouvert(item["date_limite"]):
            ignores_clos += 1
            continue

        vus_ce_run.add(item["id"])
        nouveaux.append(item)
        if limite is not None and len(nouveaux) >= limite:
            print(f"ARMP : plafond premier lancement atteint ({limite} avis).")
            break

    if ignores_clos:
        print(f"  ARMP : {ignores_clos} avis deja clos ecarte(s).")
    return nouveaux


class ArmpScraper(BaseScraper):
    source_key = "armp"
    nom = "ARMP Madagascar"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
