"""Marches publics du Mali (DGMP, Direction Generale des Marches Publics).

Sources : https://www.dgmp.gouv.ml/?q=node/71  (appels d'offres)
          https://www.dgmp.gouv.ml/?q=node/66  (manifestations d'interet)

Constate le 14/09/2026 :

  - Chaque page rend UN tableau complet, de 2020 a aujourd'hui, sans
    pagination : 1 837 et 1 082 lignes. La classe "DataTable" ne sert qu'au
    tri et au filtrage cote navigateur ; le HTML contient tout.

  - Cinq colonnes : autorite contractante, service, libelle du dossier, date
    du dossier (JJ/MM/AAAA), lien vers le dossier. Ni date limite, ni
    reference de marche, ni fiche detaillee.

  - Le lien du dossier pointe vers un fichier nomme
    `<numero>_<type>_<numero>.docx|pdf` : le premier numero est unique sur
    les 1 616 lignes qui en ont un, et sert d'identifiant. Les 221 lignes
    sans dossier sont identifiees par le hachage de leur contenu.

  - Le tableau est trie par date decroissante, mais on ne s'y fie pas : le
    filtre d'age s'applique ligne par ligne.
"""

import hashlib
import re
import time
from datetime import date, timedelta

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import ML_BASE, ML_LISTES, ML_PAGE_DELAY, ML_MAX_JOURS, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html",
           "Accept-Language": "fr"}

#: Colonnes du tableau, dans l'ordre ou le portail les rend.
AUTORITE, SERVICE, LIBELLE, DATE_DOSSIER, DOSSIER = 0, 1, 2, 3, 4

NUMERO_FICHIER = re.compile(r"/(\d+)_[A-Z]+_\d+\.\w+$")


def texte_brut(cellule) -> str:
    return re.sub(r"\s+", " ", cellule.get_text(" ", strip=True)).strip()


def date_iso(brut: str) -> str:
    """"28/07/2026" -> "2026-07-28", vide si illisible."""
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", brut or "")
    if not m:
        return ""
    jour, mois, annee = (int(x) for x in m.groups())
    try:
        return date(annee, mois, jour).isoformat()
    except ValueError:
        return ""


def identifiant(lien: str, autorite: str, libelle: str, publie: str) -> str:
    """Numero du fichier joint quand il y en a un, sinon hachage du contenu."""
    m = NUMERO_FICHIER.search(lien or "")
    if m:
        return f"ml-{m.group(1)}"
    graine = f"{autorite}|{libelle}|{publie}".encode("utf-8")
    return "ml-" + hashlib.sha1(graine).hexdigest()[:12]


def lignes_du_tableau(html: str) -> list:
    """Les lignes de donnees du tableau, en-tete exclue.

    Une ligne qui n'a pas cinq cellules est ignoree : la mise en page a
    change, et lire la date dans la colonne du service produirait des
    dates fausses en silence.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []
    lignes = []
    for tr in table.find_all("tr"):
        cellules = tr.find_all("td")
        if len(cellules) < 5:
            continue
        lignes.append(cellules)
    return lignes


def normalize(cellules: list, nature: str) -> dict:
    autorite = texte_brut(cellules[AUTORITE])
    service = texte_brut(cellules[SERVICE])
    libelle = texte_brut(cellules[LIBELLE])
    publie = date_iso(texte_brut(cellules[DATE_DOSSIER]))
    a = cellules[DOSSIER].find("a", href=True)
    lien = a["href"] if a else ""
    if lien.startswith("./"):
        lien = ML_BASE + lien[1:]
    elif lien.startswith("/"):
        lien = ML_BASE + lien

    details = [nature]
    if service and service != autorite:
        details.append(f"Service {service}")

    return {
        "id": identifiant(lien, autorite, libelle, publie),
        "source": "mali",
        "titre": libelle,
        "organisation": autorite,
        "pays": "Mali",
        "date_limite": "",
        "date_publication": publie,
        "description": ". ".join(details + [libelle]),
        # A defaut de fiche, le dossier lui-meme ; la page de la liste sinon.
        "lien": lien or ML_LISTES[0][0],
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Lit les deux tableaux et garde les dossiers recents et inconnus.

    `complet` leve le filtre d'age : on remonte alors tout le catalogue, ce
    qui n'a de sens que pour une analyse retrospective.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    plancher = (date.today() - timedelta(days=ML_MAX_JOURS)).isoformat()

    for rang, (url, nature) in enumerate(ML_LISTES):
        if rang > 0 and ML_PAGE_DELAY:
            time.sleep(ML_PAGE_DELAY)     # consigne du robots.txt
        try:
            html = get_html(url, HEADERS, timeout=60)
        except Exception as exc:
            print(f"Mali : {nature}, page inaccessible ({str(exc)[:70]}).")
            continue

        lignes = lignes_du_tableau(html)
        if not lignes:
            print(f"Mali : {nature}, aucun avis reconnu -- la mise en page "
                  f"a peut-etre change.")
            continue

        for cellules in lignes:
            item = normalize(cellules, nature)
            if not item["titre"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            if not complet and (not item["date_publication"]
                                or item["date_publication"] < plancher):
                continue
            vus_ce_run.add(item["id"])
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                print(f"Mali : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

    return nouveaux


class MaliScraper(BaseScraper):
    source_key = "mali"
    nom = "Mali (DGMP)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
