"""Appels d'offres et recrutements du WWF Madagascar.

Source : https://www.wwf.mg/rejoignez_nous3/emploi/

La page melange deux natures d'annonces :
  - des appels d'offres et consultances ("Acquisition de materiels
    informatiques", "APPEL D'OFFRES - Acquisition de six Laptops") ;
  - des postes salaries ("Un.e (01) Executive Assistant").

On collecte les deux : c'est le tri par le LLM qui fait le depart, son prompt
ecartant deja les postes salaries sans prestation externalisable. Filtrer ici
sur le titre serait fragile -- un intitule comme "AVIS DE RECRUTEMENT" designe
tantot un poste, tantot une consultance.

Constate le 21/08/2026 :
  - robots.txt autorise ce chemin et impose "Crawl-delay: 10".
  - Une seule page, sans pagination : une requete par execution, le delai ne
    joue donc pas en pratique.
  - La liste ne porte pas de date limite de depot, seulement une date de
    publication ("14 Aug 2026"). D'ou le filtre sur la fraicheur.
"""

import re
import time
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html
from Offre.sources import (
    WWF_BASE_URL,
    WWF_MAX_JOURS,
    WWF_PAGE_DELAY,
    FIRST_RUN_MAX_ITEMS,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.8",
}

# Le site date en anglais ("14 Aug 2026") : abreviations non ambigues,
# contrairement au francais ou "jui" vaut juin comme juillet.
MOIS_EN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def date_publication(texte: str):
    """Extrait "14 Aug 2026" -> date(2026, 8, 14). None si illisible."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(20\d{2})", texte or "")
    if not m:
        return None
    jour, mois_txt, annee = m.groups()
    mois = MOIS_EN.get(mois_txt[:3].lower())
    if not mois:
        return None
    try:
        return date(int(annee), mois, int(jour))
    except ValueError:
        return None


def identifiant(lien: str) -> str:
    """L'identifiant numerique du CMS ("?21282841/Titre") sert de cle."""
    m = re.search(r"\?(\d{5,})/", lien or "")
    return f"wwf-{m.group(1)}" if m else ""


def lien_absolu(href: str) -> str:
    """Les liens sont relatifs a la page de liste ("?21282841/Titre")."""
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return WWF_BASE_URL.rstrip("/") + "/" + href.lstrip("/")


def est_recent(publie) -> bool:
    """Vrai si l'annonce est assez recente pour etre encore ouverte.

    Aucune date limite n'est publiee sur la liste : la fraicheur est le seul
    indice disponible. Une annonce sans date lisible est conservee, on ne peut
    pas affirmer qu'elle est close.
    """
    if publie is None:
        return True
    return (date.today() - publie).days <= WWF_MAX_JOURS


def fetch_avis() -> list:
    """Recupere et parse la page unique."""
    soup = BeautifulSoup(get_html(WWF_BASE_URL, HEADERS, timeout=60), "html.parser")

    avis = []
    for item in soup.select(".list-item"):
        titre_el = item.select_one(".item-title")
        if titre_el is None:
            continue
        # Le texte complet du bloc porte titre, extrait et date : la date
        # n'a pas de conteneur dedie.
        contenu = re.sub(r"\s+", " ", item.get_text(" ", strip=True))
        avis.append({
            "titre": titre_el.get_text(" ", strip=True),
            "lien": titre_el.get("href", ""),
            "contenu": contenu,
        })
    return avis


#: Mois francais, pour les annonces qui ecrivent la date en toutes lettres.
MOIS_FR = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "aout": 8, "août": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}

#: Les trois graphies rencontrees : 23/09/2026, 13/09/26, 03 septembre 2026.
_DATE = re.compile(
    r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b"
    r"|\b(\d{1,2})\s+(" + "|".join(MOIS_FR) + r")\s+(\d{4})\b", re.I)

#: Ce qui designe la remise des offres. Une annonce en porte plusieurs
#: echeances : questions, reponses, visite de site, livraison. On ne veut que
#: celle du depot.
_DEPOT = re.compile(r"offres?|soumission|soumissionnaire|pli|candidature|"
                    r"d[ée]p[ôo]t|dossier|proposition|"
                    # Certaines annonces ne nomment jamais l'objet depose :
                    # "Ou envoyes a l'adresse ... Au plus tard le 14/09/26".
                    r"envoy|parvenir|transmis|prestation", re.I)

#: Ce qui designe une AUTRE echeance. Constate : une annonce demande les
#: questions "au plus tard le 13/09", les reponses "au plus tard le 16/09",
#: et les offres "au plus tard le 23/09" ; une autre fixe la remise au
#: 03 septembre et la LIVRAISON au 10 -- prendre la date la plus tardive
#: donnerait donc la mauvaise.
#: Ces mots l'emportent sur ceux de _DEPOT : la phrase des questions dit
#: "doivent etre ENVOYEES ... au plus tard", ce qui ressemble a un depot.
#: Sans accent obligatoire -- les annonces melangent "eclaircissement" et
#: "eclaircissement".
_AUTRE_ECHEANCE = re.compile(r"livr|question|clarification|r[ée]ponse|visite|"
                             r"communiqu|renseignement|[ée]claircissement", re.I)


def _en_date(m):
    """Transforme une correspondance de _DATE en date, ou None."""
    if m.group(1):
        jour, mois, annee = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if annee < 100:            # "13/09/26"
            annee += 2000
    else:
        jour = int(m.group(4))
        mois = MOIS_FR[m.group(5).lower()]
        annee = int(m.group(6))
    try:
        return date(annee, mois, jour)
    except ValueError:
        return None


def date_limite_depuis_fiche(texte: str):
    """Trouve la date de remise des offres dans le texte d'une annonce.

    Renvoie une date ISO, ou "" si rien de sur. Une date FAUSSE serait pire
    que pas de date : elle ferait passer une offre ouverte pour close, ou
    l'inverse. En cas de doute, on ne rend rien.

    La recherche est SEMANTIQUE et non positionnelle. Une annonce du WWF porte
    couramment quatre echeances -- questions, reponses, visite de site,
    livraison -- et ni la premiere ni la derniere n'est celle du depot.
    """
    if not texte:
        return ""

    candidates = []
    for m in _DATE.finditer(texte):
        jour = _en_date(m)
        if jour is None:
            continue
        # Le qualificatif PRECEDE toujours la date -- "au plus tard le X",
        # "livrees avant le X". On ne regarde donc pas apres : une premiere
        # version prenait 60 caracteres en aval et y attrapait le "LIVRAISON"
        # de la phrase SUIVANTE, ce qui faisait rejeter la bonne date.
        contexte = texte[max(0, m.start() - 200):m.start()]
        # Borner a la phrase courante : la precedente parle souvent d'une
        # autre echeance, et ses mots fausseraient le jugement.
        contexte = contexte.rsplit(". ", 1)[-1]
        if _AUTRE_ECHEANCE.search(contexte):
            continue
        if _DEPOT.search(contexte):
            candidates.append(jour)

    if not candidates:
        return ""
    # Plusieurs mentions du meme depot arrivent (rappel en fin d'annonce) :
    # la plus tardive est la bonne, un rappel ne devance jamais l'echeance.
    return max(candidates).isoformat()


def normalize(brut: dict) -> dict:
    """Ramene une annonce au format commun aux autres sources."""
    publie = date_publication(brut["contenu"])
    titre = brut["titre"]

    # L'extrait est le contenu prive du titre et de la date.
    extrait = brut["contenu"]
    if titre and extrait.startswith(titre):
        extrait = extrait[len(titre):].strip()

    # L'echeance n'est PAS dans la liste : scrape_new_avis va la chercher sur
    # la fiche, apres coup. normalize n'a pas acces au reseau.
    limite = brut.get("date_limite", "")

    details = [f"Publié le {publie}" if publie else "Date de publication inconnue",
               f"Remise des offres le {limite}" if limite
               else "Date limite non trouvée dans l'annonce"]

    return {
        "id": identifiant(brut["lien"]),
        "source": "wwf",
        "titre": titre,
        "organisation": "WWF Madagascar",
        "pays": "Madagascar",
        # Absente de la LISTE, mais presente dans le corps de l'annonce :
        # date_limite_depuis_fiche l'y cherche. Vide si rien de sur -- une
        # date fausse ferait passer une offre ouverte pour close.
        "date_limite": limite,
        # Seul repere d'age pour cette source, qui ne publie pas d'echeance.
        "date_publication": publie or "",
        "description": ". ".join(details) + ". " + extrait[:1200],
        "lien": lien_absolu(brut["lien"]),
    }


def echeance_de_l_annonce(lien: str) -> str:
    """Ouvre la fiche d'une annonce et y cherche la date de remise.

    Couteux : le robots.txt du site impose "Crawl-delay: 10", soit dix
    secondes par annonce. On ne l'appelle donc que sur les annonces NOUVELLES,
    jamais sur l'ensemble de la liste.

    Rend "" en cas d'echec : une offre sans echeance reste affichee, une offre
    mal datee induirait en erreur.
    """
    if not lien:
        return ""
    try:
        soup = BeautifulSoup(get_html(lien, HEADERS, timeout=60), "html.parser")
    except Exception as exc:
        print(f"  WWF : fiche illisible ({str(exc)[:60]})")
        return ""
    texte = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    return date_limite_depuis_fiche(texte)


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les annonces inconnues et suffisamment recentes.

    Pas de pagination : la page porte l'integralite des annonces en cours.
    Le mode complet ne change donc rien, sinon l'absence de plafond.
    """
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    nouveaux = []
    vus_ce_run = set()
    ignores_anciens = 0

    for brut in fetch_avis():
        item = normalize(brut)
        if not item["id"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
            continue
        if not complet and not est_recent(date_publication(brut["contenu"])):
            ignores_anciens += 1
            continue

        vus_ce_run.add(item["id"])
        # La fiche, pour l'echeance. Apres le filtre de fraicheur et le
        # controle des doublons : inutile de payer dix secondes pour une
        # annonce qu'on va ecarter.
        if nouveaux:
            time.sleep(WWF_PAGE_DELAY)
        item["date_limite"] = echeance_de_l_annonce(item["lien"])
        if item["date_limite"]:
            item["description"] = item["description"].replace(
                "Date limite non trouvée dans l'annonce",
                f"Remise des offres le {item['date_limite']}")
        nouveaux.append(item)
        if limite is not None and len(nouveaux) >= limite:
            print(f"WWF : plafond premier lancement atteint ({limite} annonces).")
            break

    if ignores_anciens:
        print(f"  WWF : {ignores_anciens} annonce(s) trop ancienne(s) ecartee(s).")
    return nouveaux


class WwfScraper(BaseScraper):
    source_key = "wwf"
    nom = "WWF Madagascar"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
