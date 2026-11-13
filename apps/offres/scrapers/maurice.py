"""Marches publics de Maurice (Public Procurement Portal).

Source : https://publicprocurement.govmu.org/publicprocurement/?page_id=720

Portail officiel ou les organismes publics mauriciens publient leurs avis.
WordPress 6.9.4, sans pare-feu ; le site ne sert aucun robots.txt.

Constate le 25/08/2026 :

  - La page n'affiche que les avis EN COURS -- 20 le jour du branchement --
    sans pagination ni archive. Une seule requete suffit donc, et un avis
    disparait de la page a sa cloture.

  - Chaque avis est un <div class="row"> de huit colonnes exactement, les
    quatre premieres portant l'organisme, la reference, la categorie et la
    description, la cinquieme la date de cloture. Structure verifiee sur les
    21 blocs de la page : 21 fois huit colonnes, sans exception.

  - L'API REST existe mais ne sert a rien ici : elle repond par la route
    ?rest_route= (le chemin /wp-json renvoie 404), et les avis ne sont pas un
    type de contenu -- ils vivent dans le corps Elementor de la page 720.
    Le HTML reste donc la seule voie.

ELIGIBILITE : le Public Procurement Act mauricien prevoit l'International
Bidding, une societe malgache peut soumissionner. Les fournisseurs locaux
beneficient d'une marge de preference de 30 a 40 %.
"""

import hashlib
import re
from datetime import date
from html import unescape

from .base import BaseScraper
from .http import get_html
from Offre.sources import MAURICE_URL, MAURICE_BASE, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}

#: Mois anglais en toutes lettres, seul format employe par le portail.
MOIS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

#: Intitules de la ligne d'en-tete, a ne pas prendre pour un avis.
ENTETE = "public body"

#: Colonnes utiles, dans l'ordre ou le portail les rend.
ORGANISME, REFERENCE, CATEGORIE, DESCRIPTION, CLOTURE = 0, 1, 2, 3, 4


def texte_brut(html: str) -> str:
    """Retire balises et entites d'une cellule."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def date_cloture(brut: str) -> str:
    """Extrait la date de "22 September 2026 14:00" -> "2026-09-22".

    L'heure est ignoree : elle s'ecrit tantot "14:00", tantot "13.30", et le
    reste du pipeline ne raisonne qu'en jours. Certains avis n'en portent
    d'ailleurs aucune.
    """
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", brut or "")
    if not m:
        return ""
    jour, mois_txt, annee = m.groups()
    mois = MOIS_EN.get(mois_txt.lower())
    if not mois:
        return ""
    try:
        return date(int(annee), mois, int(jour)).isoformat()
    except ValueError:
        return ""


def identifiant(reference: str, description: str) -> str:
    """Identifiant stable, derive du contenu de la ligne.

    Le portail n'expose aucun identifiant technique. La reference du marche
    serait le candidat naturel, mais un avis sur vingt n'en porte pas, et
    certaines lignes y mettent un intitule ("REGISTRATION OF SUPPLIERS")
    plutot qu'une reference. On hache donc reference et description ensemble.

    Consequence assumee : si l'organisme corrige une coquille dans la
    description, l'avis reapparait comme neuf. Mieux vaut un doublon
    occasionnel qu'une collision entre deux marches distincts.
    """
    graine = f"{reference}|{description}".encode("utf-8")
    return "maurice-" + hashlib.sha1(graine).hexdigest()[:12]


def premier_lien(bloc: str) -> str:
    """Lien vers l'avis detaille, absolu. Vide si l'organisme n'en joint pas."""
    m = re.search(r"""href=['"]([^'"]+)['"]""", bloc)
    if not m:
        return MAURICE_URL
    lien = m.group(1)
    return MAURICE_BASE + lien if lien.startswith("/") else lien


def normalize(colonnes: list, bloc: str) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    organisme = texte_brut(colonnes[ORGANISME])
    reference = texte_brut(colonnes[REFERENCE])
    categorie = texte_brut(colonnes[CATEGORIE])
    description = texte_brut(colonnes[DESCRIPTION])

    details = []
    if reference:
        details.append(f"Reference {reference}")
    if categorie:
        details.append(f"Categorie {categorie}")

    return {
        "id": identifiant(reference, description),
        "source": "maurice",
        # La description EST l'objet du marche ; le portail ne publie pas de
        # titre distinct. La tronquer priverait le tri de sa seule matiere.
        "titre": description or f"Avis {reference}" or "Avis Maurice",
        "organisation": organisme,
        "pays": "Maurice",
        "date_limite": date_cloture(texte_brut(colonnes[CLOTURE])),
        "description": ". ".join(details + [description]),
        "lien": premier_lien(bloc),
    }


def lignes_de_la_page(html: str) -> list:
    """Decoupe la page en blocs d'avis, en-tete exclue.

    Un bloc valide porte exactement huit colonnes : moins signifie que la mise
    en page a change, auquel cas on prefere ignorer la ligne plutot que de
    lire un champ pour un autre.
    """
    compact = re.sub(r"\s+", " ", html or "")
    blocs = []
    for bloc in re.split(r'<div class="row"', compact)[1:]:
        colonnes = re.findall(r'<div class="col-sm-\d"[^>]*>(.*?)</div>', bloc)
        if len(colonnes) < 8:
            continue
        if texte_brut(colonnes[ORGANISME]).lower() == ENTETE:
            continue
        blocs.append((colonnes, bloc))
    return blocs


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus.

    La page ne listant que les marches en cours, il n'y a ni pagination a
    parcourir ni avis clos a ecarter. Le parametre `complet` est accepte pour
    respecter la signature commune, mais ne change rien.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    try:
        html = get_html(MAURICE_URL, HEADERS, timeout=45)
    except Exception as exc:
        print(f"Maurice : page inaccessible ({str(exc)[:70]}).")
        return []

    blocs = lignes_de_la_page(html)
    if not blocs:
        # Le portail est vivant mais nous ne reconnaissons plus sa mise en
        # page : le signaler vaut mieux que de rendre zero en silence.
        print("Maurice : aucun avis reconnu, la mise en page a peut-etre change.")
        return []

    for colonnes, bloc in blocs:
        item = normalize(colonnes, bloc)
        if not item["titre"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
            continue
        vus_ce_run.add(item["id"])
        nouveaux.append(item)
        if limite is not None and len(nouveaux) >= limite:
            print(f"Maurice : plafond premier lancement atteint ({limite} avis).")
            break

    return nouveaux


class MauriceScraper(BaseScraper):
    source_key = "maurice"
    nom = "Maurice (marches publics)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
