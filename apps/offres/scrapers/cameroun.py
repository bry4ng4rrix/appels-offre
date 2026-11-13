"""Marches publics du Cameroun (ARMP, Journal des Marches).

Source : https://www.armp.cm/filtres?type=avis&val=<type>&page=<n>

Portail de l'Agence de Regulation des Marches Publics. Constate le 14/09/2026 :

  - Six listes, une par type d'avis, paginees par 10 et triees par date de
    publication decroissante. Le volume est le plus gros de toutes les
    sources nationales sondees : 7 367 appels d'offres nationaux, 1 407
    demandes de cotation, 577 manifestations d'interet, 184 appels d'offres
    internationaux.

  - Chaque entree de liste est un <div class="col-md-10"> qui porte le titre
    dans un <strong class="text-uppercase">, puis des lignes "libelle :
    valeur" en <div class="d-table-row"> : MO/AC (maitre d'ouvrage), Type,
    Region, Montant, Publie le, Date de cloture, Heure de cloture.

  - Les filtres sont poreux : la liste "international" (val=4) contient
    aussi des appels d'offres nationaux, et toutes contiennent des
    communiques (COMM) et additifs (ADDITIF) qui n'ont pas d'echeance -- le
    portail y ecrit 01-01-1970. Le type qui fait foi est celui du lien de la
    fiche, `details?type_publication=AO|AMI|DC|COMM|ADDITIF&id_publication=N`,
    pas celui de la liste parcourue.

  - La fiche detaillee est structuree en rubriques numerotees ("1.Objet",
    "2.Consistance des prestations", "4.Participation et origine"...). C'est
    la que se trouve la substance : la liste ne donne que l'intitule
    administratif ("AVIS D'APPEL D'OFFRES NATIONAL OUVERT N 10A/AONO/..."),
    qui ne dit rien de l'objet. On va donc chercher la fiche de chaque avis
    nouveau -- une requete par avis, avec un delai de politesse.

ELIGIBILITE : la rubrique "Participation et origine" precise si les
entreprises etrangeres sont admises ("siege social en Republique du Cameroun
ou a l'etranger"). Elle est reprise dans la description pour que le tri
puisse ecarter les avis reserves aux nationaux.
"""

import re
import time
from datetime import date
from html import unescape

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (CM_LISTE, CM_DETAIL, CM_TYPES, CM_TYPES_EXCLUS,
                    CM_PAGE_DELAY, CM_MAX_PAGES, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html",
           "Accept-Language": "fr"}

#: Code du lien de la fiche -> nature de l'avis. C'est lui qui fait foi : la
#: colonne "Type" des listes repete le filtre parcouru, pas l'avis.
NATURES = {"AO": "Appel d'offres", "AMI": "Manifestation d'interet",
           "DC": "Demande de cotation", "DP": "Demande de proposition"}

#: Rubriques de la fiche reprises dans la description, dans cet ordre.
#: Le numero est ignore a la comparaison : "1.Objet" et "1. Objet" coexistent.
RUBRIQUES = ("objet", "consistance des prestations", "participation et origine")
LONGUEUR_MAX_RUBRIQUE = 700

LIEN_FICHE = re.compile(r"type_publication=(\w+)&(?:amp;)?id_publication=(\d+)")


def texte_brut(html) -> str:
    return re.sub(r"\s+", " ", unescape(str(html or ""))).strip()


def date_iso(brut: str) -> str:
    """"09-09-2026 15:59:49" -> "2026-09-09". Vide si absente ou 1970.

    01-01-1970 est la valeur nulle du portail (epoch Unix rendue comme une
    date) : elle marque un communique, pas une echeance au 1er janvier 1970.
    """
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", brut or "")
    if not m:
        return ""
    jour, mois, annee = (int(x) for x in m.groups())
    if annee <= 1970:
        return ""
    try:
        return date(annee, mois, jour).isoformat()
    except ValueError:
        return ""


def entrees_de_la_page(html: str) -> list:
    """Decoupe une page de liste en avis bruts.

    Chaque avis est un dict : type_publication, id_publication, titre, et
    les champs "libelle -> valeur" de la liste. Une entree sans lien vers sa
    fiche est ignoree : sans identifiant, rien ne la distingue d'une autre.
    """
    soup = BeautifulSoup(html, "html.parser")
    avis = []
    for titre in soup.select("div.col-md-10 strong.text-uppercase"):
        bloc = titre.find_parent("div", class_="col-md-10")
        lien = bloc.find("a", href=LIEN_FICHE) if bloc else None
        if not lien:
            continue
        m = LIEN_FICHE.search(lien["href"])
        champs = {}
        for ligne in bloc.select("div.d-table-row"):
            cellules = ligne.find_all("div", recursive=False)
            if len(cellules) >= 2:
                cle = texte_brut(cellules[0].get_text(" ")).rstrip(": ").strip()
                champs[cle] = texte_brut(cellules[1].get_text(" "))
        avis.append({
            "type_publication": m.group(1),
            "id_publication": m.group(2),
            # L'attribut title porte l'intitule complet ; le texte visible est
            # parfois tronque par la mise en page (line-clamp).
            "titre": texte_brut(titre.get("title") or titre.get_text(" ")),
            **champs,
        })
    return avis


def rubriques_de_la_fiche(html: str) -> dict:
    """Extrait les rubriques numerotees de la fiche : {"objet": "...", ...}.

    Chaque rubrique est un <strong> "N.Libelle" suivi d'un bloc de texte.
    On indexe sur le libelle en minuscules, sans son numero.
    """
    soup = BeautifulSoup(html, "html.parser")
    rubriques = {}
    for strong in soup.find_all("strong"):
        libelle = texte_brut(strong.get_text(" "))
        m = re.match(r"\d+\s*\.\s*(.+?)(?:\s*New\(Additif\))?$", libelle)
        if not m:
            continue
        cle = m.group(1).strip().lower()
        entete = strong.find_parent("div")
        corps = entete.find_next_sibling("div") if entete else None
        if corps is None:
            continue
        rubriques[cle] = texte_brut(corps.get_text(" "))
    return rubriques


def fiche(type_publication: str, id_publication: str) -> dict:
    """Va chercher la fiche et renvoie ses rubriques ; {} si elle echoue.

    Un echec n'est pas bloquant : l'avis sera charge avec son seul intitule,
    comme le fait la BAD, plutot que perdu.
    """
    try:
        html = get_html(CM_DETAIL, HEADERS,
                        params={"type_publication": type_publication,
                                "id_publication": id_publication}, timeout=45)
    except Exception as exc:
        print(f"  Cameroun : fiche {type_publication}/{id_publication} "
              f"inaccessible ({str(exc)[:60]}).")
        return {}
    return rubriques_de_la_fiche(html)


def normalize(brut: dict, rubriques: dict) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    code = brut["type_publication"]
    details = [NATURES.get(code, code)]
    for cle in ("Région", "Montant"):
        if brut.get(cle):
            details.append(f"{cle} {brut[cle]}")
    for cle in RUBRIQUES:
        valeur = rubriques.get(cle, "")
        if valeur:
            details.append(f"{cle.capitalize()} : {valeur[:LONGUEUR_MAX_RUBRIQUE]}")

    return {
        "id": f"cm-{brut['type_publication'].lower()}-{brut['id_publication']}",
        "source": "cameroun",
        "titre": brut["titre"],
        "organisation": brut.get("MO/AC", ""),
        "pays": "Cameroun",
        "date_limite": date_iso(brut.get("Date de clôture", "")),
        "date_publication": date_iso(brut.get("Publié le", "")),
        "description": ". ".join(details),
        "lien": (f"{CM_DETAIL}?type_publication={brut['type_publication']}"
                 f"&id_publication={brut['id_publication']}"),
    }


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Parcourt chaque liste de type, page par page, jusqu'a une page connue.

    Meme logique que la BAD : l'arret porte sur une page entierement connue
    et non sur le premier ID connu. Un avis clos (echeance passee) n'est pas
    collecte : il est inutile, et sur un premier lancement il consommerait
    le plafond a la place d'un avis ouvert.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    aujourd_hui = date.today().isoformat()

    for val, libelle_type in CM_TYPES:
        for page in range(1, CM_MAX_PAGES + 1):
            if CM_PAGE_DELAY:
                time.sleep(CM_PAGE_DELAY)
            try:
                html = get_html(CM_LISTE, HEADERS,
                                params={"type": "avis", "val": val, "page": page},
                                timeout=45)
            except Exception as exc:
                print(f"Cameroun : {libelle_type} page {page} inaccessible "
                      f"({str(exc)[:60]}).")
                break

            bruts = entrees_de_la_page(html)
            if not bruts:
                if page == 1:
                    print(f"Cameroun : {libelle_type}, aucun avis reconnu -- "
                          f"la mise en page a peut-etre change.")
                break

            # On compte les avis INCONNUS de la base, clos compris : un avis
            # clos et ignore reste une nouveaute, et une page qui n'en
            # contiendrait que de tels ne doit pas passer pour deja vue.
            inconnus_page = 0
            for brut in bruts:
                if brut["type_publication"] in CM_TYPES_EXCLUS:
                    continue
                ident = f"cm-{brut['type_publication'].lower()}-{brut['id_publication']}"
                if ident in seen_ids or ident in vus_ce_run:
                    continue
                vus_ce_run.add(ident)
                inconnus_page += 1
                echeance = date_iso(brut.get("Date de clôture", ""))
                if echeance and echeance < aujourd_hui:
                    continue

                time.sleep(CM_PAGE_DELAY)
                rubriques = fiche(brut["type_publication"], brut["id_publication"])
                nouveaux.append(normalize(brut, rubriques))
                if limite is not None and len(nouveaux) >= limite:
                    print(f"Cameroun : plafond premier lancement atteint ({limite} avis).")
                    return nouveaux

            if not complet and inconnus_page == 0:
                break

    return nouveaux


class CamerounScraper(BaseScraper):
    source_key = "cameroun"
    nom = "Cameroun (ARMP)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
