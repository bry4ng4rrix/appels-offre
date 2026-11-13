"""Marches publics du Maroc (PMMP, Portail Marocain des Marches Publics).

Source : https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch

Application PRADO : chaque commande est un POST du formulaire entier, avec
l'etat de page (PRADO_PAGESTATE) rendu par la reponse precedente et le nom de
la commande (PRADO_POSTBACK_TARGET). Constate le 14/09/2026 :

  1. GET du formulaire de recherche avancee, POST de la recherche bornee
     sur la date de mise en ligne (cible : lancerRecherche). Le POST va a
     l'action du formulaire, qui n'est pas l'URL de la page.
  2. Sur les resultats, POST du choix "100 par page" (cible :
     listePageSizeTop). 500 fait couper la connexion.
  3. Pour chaque page suivante, POST du numero de page (numPageTop, cible :
     DefaultButtonTop).

Chaque ligne du tableau porte, dans des elements identifies par
`..._ctlN_...` : la procedure (panelBlocTypesProc), la categorie
(panelBlocCategorie : Travaux, Services, Fournitures), la date de mise en
ligne, la reference, l'objet (panelBlocObjet), l'acheteur public
(panelBlocDenomination), le lieu (panelBlocLieuxExec), la date limite
(cloture-line) et le lien de la fiche, EntrepriseDetailConsultation
&refConsultation=N&orgAcronyme=X. refConsultation est l'identifiant.

Le tableau est trie par date limite decroissante ; la fenetre de dates
remplace le tri par publication qu'on aurait voulu.
"""

import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from Offre.sources import (MA_BASE, MA_FORMULAIRE, MA_FENETRE_JOURS, MA_PAGE_SIZE,
                    MA_MAX_PAGES, MA_PAGE_DELAY, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html",
           "Accept-Language": "fr"}
TIMEOUT = 180

PREFIXE = "ctl0$CONTENU_PAGE$"
CHAMP_DEBUT = PREFIXE + "AdvancedSearch$dateMiseEnLigneCalculeStart"
CHAMP_FIN = PREFIXE + "AdvancedSearch$dateMiseEnLigneCalculeEnd"
CIBLE_RECHERCHE = PREFIXE + "AdvancedSearch$lancerRecherche"
CHAMP_TAILLE = PREFIXE + "resultSearch$listePageSizeTop"
CHAMP_PAGE = PREFIXE + "resultSearch$numPageTop"
CIBLE_PAGE = PREFIXE + "resultSearch$DefaultButtonTop"

REF_CONS = re.compile(r"tableauResultSearch\$ctl\d+\$refCons$")
LIEN_FICHE = re.compile(r"refConsultation=(\d+)&(?:amp;)?orgAcronyme=(\w+)")
NB_RESULTATS = re.compile(r"Nombre de r[ée]sultats\s*:\s*(\d+)")


def texte_brut(el) -> str:
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def date_iso(brut: str) -> str:
    """"04/11/2026 10:00" -> "2026-11-04"."""
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", brut or "")
    if not m:
        return ""
    jour, mois, annee = (int(x) for x in m.groups())
    try:
        return date(annee, mois, jour).isoformat()
    except ValueError:
        return ""


def champs_du_formulaire(soup) -> tuple:
    """(action absolue, champs) du formulaire principal, tels qu'un
    navigateur les enverrait : boutons exclus, cases non cochees exclues."""
    form = soup.find("form")
    if form is None:
        return "", {}
    champs = {}
    for inp in form.find_all("input"):
        nom, genre = inp.get("name"), inp.get("type", "text")
        if not nom or genre in ("submit", "image", "button"):
            continue
        if genre in ("checkbox", "radio"):
            if inp.has_attr("checked"):
                champs[nom] = inp.get("value", "on")
            continue
        champs[nom] = inp.get("value", "")
    for sel in form.find_all("select"):
        nom = sel.get("name")
        opt = sel.find("option", selected=True) or sel.find("option")
        if nom and opt is not None:
            champs[nom] = opt.get("value", "")
    action = form.get("action", "").replace("&amp;", "&")
    if action.startswith("/"):
        action = MA_BASE + action
    return action, champs


def lignes_de_la_page(soup) -> list:
    """Une entree par ligne du tableau de resultats."""
    lignes = []
    for inp in soup.find_all("input", attrs={"name": REF_CONS}):
        tr = inp.find_parent("tr")
        if tr is None:
            continue
        prefixe = inp["name"][: -len("$refCons")].replace("$", "_")
        # Les identifiants de la ligne derivent du nom du champ cache.
        def bloc(suffixe):
            return tr.find(id=f"{prefixe}_{suffixe}")

        cellule_ref = tr.find("td", headers="cons_ref")
        publie = ""
        if cellule_ref is not None:
            m = re.search(r"\b\d{2}/\d{2}/\d{4}\b", texte_brut(cellule_ref))
            publie = m.group(0) if m else ""
        # La cellule rend "Objet : X ... X" : le texte, un lien "..." cache,
        # puis l'info-bulle qui repete le texte. On s'arrete au "...".
        objet = texte_brut(bloc("panelBlocObjet"))
        objet = re.sub(r"^Objet\s*:\s*", "", objet)
        objet = objet.split("...")[0].strip()
        acheteur = re.sub(r"^Acheteur public\s*:\s*", "",
                          texte_brut(bloc("panelBlocDenomination")))
        # L'info-bulle ("MAROC, TETOUAN") repete le bloc visible ; on lit
        # l'une ou l'autre, pas les deux.
        bulle = tr.find(id=re.compile(re.escape(prefixe) + r"_ctl\d+_infosLieuExecution$"))
        lieu = texte_brut(bulle) if bulle is not None else \
            re.sub(r"\s*\.\.\.\s*", " ", texte_brut(bloc("panelBlocLieuxExec"))).strip()
        cloture = tr.find("td", headers="cons_dateEnd")
        lien = tr.find("a", href=LIEN_FICHE)
        lignes.append({
            "ref_cons": inp.get("value", ""),
            "org": (tr.find("input", attrs={"name": inp["name"].replace("refCons", "orgCons")}) or {}).get("value", ""),
            "procedure": texte_brut(bloc("panelBlocTypesProc")),
            "categorie": texte_brut(bloc("panelBlocCategorie")),
            "publie": publie,
            "reference": texte_brut(bloc("reference")),
            "objet": objet,
            "acheteur": acheteur,
            "lieu": lieu,
            "cloture": texte_brut(cloture.find(class_="cloture-line")) if cloture else "",
            "lien": lien["href"].replace("&amp;", "&") if lien else "",
        })
    return lignes


def normalize(brut: dict) -> dict:
    details = [x for x in (brut["procedure"], brut["categorie"]) if x]
    if brut["reference"]:
        details.append(f"Reference {brut['reference']}")
    if brut["lieu"]:
        details.append(f"Lieu {brut['lieu']}")
    lien = brut["lien"]
    if lien.startswith("?"):
        lien = MA_BASE + "/index.php" + lien
    elif lien and not lien.startswith("http"):
        lien = MA_BASE + "/" + lien.lstrip("/")
    return {
        "id": f"ma-{brut['ref_cons']}",
        "source": "maroc",
        "titre": brut["objet"] or f"Consultation {brut['reference']}",
        "organisation": brut["acheteur"],
        "pays": "Maroc",
        "date_limite": date_iso(brut["cloture"]),
        "date_publication": date_iso(brut["publie"]),
        "description": ". ".join(details + [brut["objet"]]),
        "lien": lien or MA_FORMULAIRE,
    }


def _post(session, url, champs):
    reponse = session.post(url, data=champs, headers=HEADERS, timeout=TIMEOUT)
    reponse.raise_for_status()
    return BeautifulSoup(reponse.text, "html.parser")


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Recherche bornee sur la date de mise en ligne, puis pages de 100.

    `complet` elargit la fenetre a 30 jours ; au-dela, le volume (une
    centaine par jour) et la lenteur du portail (30 s la page) rendent la
    collecte deraisonnable.
    """
    nouveaux = []
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)
    fenetre = 30 if complet else MA_FENETRE_JOURS
    aujourd_hui = date.today()

    session = requests.Session()
    try:
        reponse = session.get(MA_FORMULAIRE, headers=HEADERS, timeout=TIMEOUT)
        reponse.raise_for_status()
        action, champs = champs_du_formulaire(BeautifulSoup(reponse.text, "html.parser"))
        if not action or "PRADO_PAGESTATE" not in champs:
            print("Maroc : formulaire de recherche non reconnu, le portail a peut-etre change.")
            return []
        champs[CHAMP_DEBUT] = (aujourd_hui - timedelta(days=fenetre)).strftime("%d/%m/%Y")
        champs[CHAMP_FIN] = aujourd_hui.strftime("%d/%m/%Y")
        champs["PRADO_POSTBACK_TARGET"] = CIBLE_RECHERCHE
        champs["PRADO_POSTBACK_PARAMETER"] = ""
        soup = _post(session, action, champs)

        total = NB_RESULTATS.search(soup.get_text(" "))
        if not total:
            print("Maroc : la recherche n'a pas rendu de resultats -- le formulaire a peut-etre change.")
            return []
        print(f"  Maroc : {total.group(1)} consultation(s) mises en ligne sur {fenetre} jour(s).")

        # 100 par page.
        time.sleep(MA_PAGE_DELAY)
        action, champs = champs_du_formulaire(soup)
        champs[CHAMP_TAILLE] = str(MA_PAGE_SIZE)
        champs["PRADO_POSTBACK_TARGET"] = CHAMP_TAILLE
        champs["PRADO_POSTBACK_PARAMETER"] = ""
        soup = _post(session, action, champs)
    except Exception as exc:
        print(f"Maroc : recherche impossible ({str(exc)[:70]}).")
        return []

    for page in range(1, MA_MAX_PAGES + 1):
        if page > 1:
            time.sleep(MA_PAGE_DELAY)
            try:
                action, champs = champs_du_formulaire(soup)
                champs[CHAMP_PAGE] = str(page)
                champs["PRADO_POSTBACK_TARGET"] = CIBLE_PAGE
                champs["PRADO_POSTBACK_PARAMETER"] = ""
                soup = _post(session, action, champs)
            except Exception as exc:
                print(f"Maroc : page {page} inaccessible ({str(exc)[:70]}).")
                print(f"  {len(nouveaux)} avis deja collecte(s) sont conserves.")
                return nouveaux

        lignes = lignes_de_la_page(soup)
        if not lignes:
            if page == 1:
                print("Maroc : aucune ligne reconnue, la mise en page a peut-etre change.")
            break

        inconnus_page = 0
        for brut in lignes:
            if not brut["ref_cons"]:
                continue
            item = normalize(brut)
            if item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            vus_ce_run.add(item["id"])
            inconnus_page += 1
            if item["date_limite"] and item["date_limite"] < aujourd_hui.isoformat():
                continue
            nouveaux.append(item)
            if limite is not None and len(nouveaux) >= limite:
                print(f"Maroc : plafond premier lancement atteint ({limite} avis).")
                return nouveaux

        if not complet and inconnus_page == 0:
            break
        if len(lignes) < MA_PAGE_SIZE:
            break

    return nouveaux


class MarocScraper(BaseScraper):
    source_key = "maroc"
    nom = "Maroc (PMMP)"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
