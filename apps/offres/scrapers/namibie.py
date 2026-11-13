"""Marches publics de Namibie (Central Procurement Board, "Open Bids").

Source : https://www.cpbn.com.na/index/external/2

Constate le 14/09/2026 :

  - La page ne liste que les avis ouverts, six au sondage, chacun dans une
    carte : un <h4 class="card-title"> dont le lien pointe vers la fiche
    index/bid/<N> et dont le texte est "Titre: REFERENCE", puis une ligne
    "Reference number: ... | Closing Date and Time: 14th October, 2026 11:00".

  - Le numero de la fiche est l'identifiant technique.

  - La fiche est un texte en paragraphes "Libelle" / valeur : Category,
    Institution, Description of the Bid, Date of Issue, Closing Date and
    Time. On en prend la categorie, l'institution et la date d'emission ;
    la description repete le titre.

ELIGIBILITE : la reference encode la methode -- ONB (Open National
Bidding), OAB (Open Advertised Bidding), OIB (Open International Bidding).
Elle figure dans la description.
"""

import re
import time
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import NA_URL, NA_DETAIL_DELAY, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}

MOIS_EN = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
           "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
           "november": 11, "december": 12}

NUMERO_FICHE = re.compile(r"/index/bid/(\d+)")

#: Libelles de la fiche dont on veut la valeur (le paragraphe suivant).
CHAMPS_FICHE = ("Category", "Institution", "Date of Issue")


def texte_brut(html) -> str:
    return re.sub(r"\s+", " ", str(html or "")).strip()


def date_iso(brut: str) -> str:
    """"14th October, 2026 11:00" -> "2026-10-14". Vide si illisible."""
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})", brut or "")
    if not m:
        return ""
    mois = MOIS_EN.get(m.group(2).lower())
    if not mois:
        return ""
    try:
        return date(int(m.group(3)), mois, int(m.group(1))).isoformat()
    except ValueError:
        return ""


def cartes_de_la_page(html: str) -> list:
    """Une entree par carte : numero, titre, reference, cloture, lien."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="activeBidsTable")
    if table is None:
        return []
    cartes = []
    for titre_el in table.select("h4.card-title"):
        a = titre_el.find("a", href=NUMERO_FICHE)
        if not a:
            continue
        numero = NUMERO_FICHE.search(a["href"]).group(1)
        brut = texte_brut(a.get_text(" "))
        carte = titre_el.find_parent("div", class_="card") or titre_el.parent
        infos = texte_brut(carte.get_text(" "))
        ref = re.search(r"Reference number:\s*(.+?)\s*\|", infos)
        cloture = re.search(r"Closing Date and Time:\s*(.+?)\s*(?:\||More Details|$)", infos)
        reference = ref.group(1).strip() if ref else ""
        # Le titre se termine par ": REFERENCE" ; on l'en debarrasse.
        titre = brut
        if reference and titre.endswith(reference):
            titre = titre[: -len(reference)].rstrip(" :-")
        cartes.append({"numero": numero, "titre": titre, "reference": reference,
                       "cloture": cloture.group(1).strip() if cloture else "",
                       "lien": a["href"]})
    return cartes


def champs_de_la_fiche(html: str) -> dict:
    """Valeur du paragraphe qui suit chacun des libelles attendus."""
    soup = BeautifulSoup(html, "html.parser")
    for x in soup(["script", "style"]):
        x.decompose()
    lignes = [texte_brut(t) for t in soup.get_text("\n").split("\n")]
    lignes = [l for l in lignes if l]
    champs = {}
    for i, ligne in enumerate(lignes[:-1]):
        cle = ligne.rstrip(":").strip()
        if cle in CHAMPS_FICHE and cle not in champs:
            champs[cle] = lignes[i + 1]
    return champs


def fiche(lien: str) -> dict:
    try:
        return champs_de_la_fiche(get_html(lien, HEADERS, timeout=60))
    except Exception as exc:
        print(f"  Namibie : fiche {lien[-12:]} inaccessible ({str(exc)[:60]}).")
        return {}


def normalize(carte: dict, champs: dict) -> dict:
    details = []
    if champs.get("Category"):
        details.append(champs["Category"])
    if carte["reference"]:
        details.append(f"Reference {carte['reference']}")
    return {
        "id": f"na-{carte['numero']}",
        "source": "namibie",
        "titre": carte["titre"],
        "organisation": champs.get("Institution", "") or "Central Procurement Board of Namibia",
        "pays": "Namibie",
        "date_limite": date_iso(carte["cloture"]),
        "date_publication": date_iso(champs.get("Date of Issue", "")),
        "description": ". ".join(details + [carte["titre"]]),
        "lien": carte["lien"],
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus. Pas de pagination, pas d'archive : une
    requete pour la liste, une par avis nouveau pour sa fiche."""
    nouveaux = []
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    try:
        html = get_html(NA_URL, HEADERS, timeout=60)
    except Exception as exc:
        print(f"Namibie : page inaccessible ({str(exc)[:70]}).")
        return []

    cartes = cartes_de_la_page(html)
    if not cartes:
        print("Namibie : aucun avis reconnu, la mise en page a peut-etre change.")
        return []

    for carte in cartes:
        ident = f"na-{carte['numero']}"
        if ident in seen_ids or any(n["id"] == ident for n in nouveaux):
            continue
        time.sleep(NA_DETAIL_DELAY)
        nouveaux.append(normalize(carte, fiche(carte["lien"])))
        if limite is not None and len(nouveaux) >= limite:
            break

    return nouveaux


class NamibieScraper(BaseScraper):
    source_key = "namibie"
    nom = "Namibie (CPBN)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
