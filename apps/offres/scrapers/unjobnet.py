"""Scraping incremental de unjobnet.org/jobs.

Les resultats sont tries du plus recent au plus ancien, mais le site epingle
des annonces en tete de liste : la collecte incrementale s'arrete donc sur une
page entierement connue, et non sur la premiere offre connue.

--- CADRE JURIDIQUE : COLLECTE NON AUTORISEE, MAINTENUE SUR DECISION ---

Les conditions d'utilisation de unjobnet.org interdisent cette collecte sur
quatre clauses cumulatives, chacune suffisante a elle seule :

    "use any robot, spider, scraper, crawler [...]"
    "harvest, scrape, bulk-download [...] in bulk"
    "republish, redistribute [...]"
    "for your own personal, non-commercial job search"

C'est le seul cas du pipeline ou la COLLECTE elle-meme est interdite, et non
la seule rediffusion. Les douze autres sources sont en regle.

Le point a ete porte a l'attention du proprietaire du projet a plusieurs
reprises. DECISION DU 25/08/2026 : la source est maintenue, en connaissance
de cause, sous sa responsabilite. Le present commentaire existe pour que la
question ne soit pas reposee a chaque relecture -- elle est tranchee -- et
pour qu'un nouvel arrivant sache que ce n'est pas un oubli.

Ce qui reste vrai et n'est pas tranche : leurs CGU invitent explicitement a
demander une licence ("requests to license or reuse our content or data").
Un brouillon de regularisation attend dans demandes-brouillons.md. L'envoyer
resoudrait le sujet plutot que de l'assumer.
"""

import re
import time

from bs4 import BeautifulSoup

from .base import BaseScraper
from .http import get_html

from Offre.sources import (
    UNJOBNET_BASE_URL,
    UNJOBNET_MAX_PAGES,
    FIRST_RUN_MAX_ITEMS,
    UNJOBNET_PAGE_DELAY,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}


def extract_id_from_url(url: str) -> str:
    """Le dernier segment de l'URL /jobs/detail/... sert d'identifiant unique."""
    return url.rstrip("/").split("/")[-1]


def find_card(link):
    """Remonte du lien titre jusqu'au conteneur complet de l'offre.

    Un simple find_parent(["article", "li", "div"]) s'arrete au premier div
    ancetre, qui n'enveloppe que le titre : l'organisation, le pays et la date
    de cloture vivent deux niveaux plus haut, dans div.job.
    """
    card = link.find_parent(class_="job")
    if card is not None:
        return card

    # Repli si le site renomme sa classe : on remonte jusqu'a l'ancetre qui
    # porte reellement le contexte de l'offre.
    node = link
    for _ in range(5):
        node = node.parent
        if node is None:
            break
        if node.select_one('a[href*="/organizations/"]'):
            return node

    return link.find_parent(["article", "li", "div"])


def premier_texte(card, selecteur: str) -> str:
    """Texte du premier lien non vide correspondant au selecteur.

    Chaque carte contient deux liens vers l'organisation : d'abord le logo
    (un <img>, donc sans texte), ensuite le nom. Un select_one() renverrait
    le logo et donc une chaine vide.
    """
    if card is None:
        return ""
    for lien in card.select(selecteur):
        texte = lien.get_text(strip=True)
        if texte:
            return texte
    return ""


def scrape_page(page: int) -> list:
    """Recupere et parse une page de resultats. Renvoie une liste de dicts."""
    url = UNJOBNET_BASE_URL if page == 1 else f"{UNJOBNET_BASE_URL}?page={page}"
    soup = BeautifulSoup(get_html(url, HEADERS), "html.parser")

    items = []
    # Selecteur robuste : cible les liens vers une fiche de poste, independant
    # des classes CSS qui peuvent changer avec le design du site.
    for link in soup.select('a[href*="/jobs/detail/"]'):
        titre = link.get_text(strip=True)
        href = link.get("href", "")
        if not titre or not href:
            continue

        job_id = extract_id_from_url(href)

        card = find_card(link)
        texte_carte = card.get_text(" ", strip=True) if card else titre

        organisation = premier_texte(card, 'a[href*="/organizations/"]')
        pays = premier_texte(card, 'a[href*="/countries/"]')

        deadline_match = re.search(r"Closes\s+(\d{1,2}\s+\w+\s+\d{4})", texte_carte)
        date_limite = deadline_match.group(1) if deadline_match else ""

        items.append({
            "id": job_id,
            "source": "unjobnet",
            "titre": titre,
            "organisation": organisation,
            "pays": pays,
            "date_limite": date_limite,
            # La carte ne contient pas le descriptif du poste : il faut ouvrir
            # la fiche (1.6 s par offre). Voir enrichir_description(), appelee
            # seulement sur les offres retenues.
            "description": "",
            "lien": f"https://www.unjobnet.org{href}" if href.startswith("/") else href,
        })

    return items


def scrape_new_jobs(seen_ids: set, complet: bool = False) -> list:
    """Parcourt les pages de la plus recente a la plus ancienne.

    Mode normal : on s'arrete des qu'une page complete ne contient aucune
    nouveaute. Le critere porte sur la page entiere et non sur la premiere
    offre connue, car le site epingle des annonces en tete de liste.

    Mode complet : on parcourt tout le catalogue en sautant simplement les IDs
    connus. C'est ce qui rend un rattrapage interrompu reprenable — sans ca, la
    reprise s'arreterait sur la premiere offre deja traitee et n'atteindrait
    jamais les plus anciennes.
    """
    nouveaux = []
    # Une meme carte contient souvent plusieurs liens vers /jobs/detail/ (titre,
    # image, "voir plus") : sans ce set, l'offre serait triee et ecrite plusieurs fois.
    vus_ce_run = set()
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    for page in range(1, UNJOBNET_MAX_PAGES + 1):
        if page > 1 and UNJOBNET_PAGE_DELAY:
            time.sleep(UNJOBNET_PAGE_DELAY)

        try:
            items = scrape_page(page)
        except Exception as exc:
            # Apres re-essais, la page reste en echec. On rend ce qui a ete
            # collecte plutot que de tout perdre : une remontee d'exception
            # ferait jeter les pages precedentes par main.collecter().
            print(f"UNjobnet : page {page} inaccessible ({str(exc)[:70]}).")
            # Le conseil depend du mode : en incremental, --complet reprendra
            # plus loin. En complet, il n'y a rien de plus a tenter -- dire
            # "utiliser --complet" a quelqu'un qui vient de le faire l'envoie
            # sur une fausse piste.
            suite = ("Relancer plus tard : le site repond par intermittence."
                     if complet else
                     "Utiliser --complet pour rattraper les pages suivantes.")
            print(f"  {len(nouveaux)} offre(s) deja collectee(s) sont "
                  f"conservees. {suite}")
            return nouveaux

        if not items:
            break

        neufs_page = 0
        for item in items:
            if item["id"] in seen_ids or item["id"] in vus_ce_run:
                continue
            vus_ce_run.add(item["id"])
            nouveaux.append(item)
            neufs_page += 1
            if limite is not None and len(nouveaux) >= limite:
                print(f"UNjobnet : plafond premier lancement atteint ({limite} offres).")
                return nouveaux

        # On s'arrete sur une page ENTIEREMENT connue, pas sur la premiere
        # offre connue : le site epingle des annonces en tete de page 1, qui
        # restent des semaines. S'arreter sur la premiere connue faisait donc
        # renvoyer 0 nouveaute a chaque run des qu'une epinglee etait vue --
        # la source etait morte silencieusement.
        if not complet and neufs_page == 0:
            return nouveaux

        if complet and page % 25 == 0:
            print(f"  UNjobnet : page {page}, {len(nouveaux)} offre(s) a traiter...")

    return nouveaux


def enrichir_description(lien: str) -> str:
    """Recupere le descriptif d'une offre depuis sa fiche.

    Couteux : ~1.6 s par offre, page de 90 Ko. A n'appeler que sur les offres
    retenues apres tri, jamais sur l'ensemble de la collecte -- sur un
    rattrapage complet cela ajouterait plus de deux heures.

    Le descriptif vit dans div#jd ("job description"). Se fier a la taille des
    blocs ne marche pas : la colonne "Similar Jobs" et le menu de categories
    sont plus volumineux que l'offre elle-meme.
    """
    try:
        soup = BeautifulSoup(get_html(lien, HEADERS), "html.parser")
    except Exception as exc:
        print(f"  Description indisponible ({str(exc)[:60]})")
        return ""

    bloc = soup.select_one("#jd") or soup.select_one(".jd")
    if bloc is None:
        # Repli si le site renomme l'ancre : on prend le plus gros bloc en
        # excluant explicitement la colonne laterale.
        for parasite in soup.select("#sidebar, nav, header, footer, script, style"):
            parasite.decompose()
        blocs = [b for b in soup.select("div, section, article")
                 if not b.find(["div", "section", "article"])]
        bloc = max(blocs, key=lambda b: len(b.get_text(strip=True)), default=None)

    if bloc is None:
        return ""

    texte = bloc.get_text("\n", strip=True)
    return re.sub(r"\n\s*\n+", "\n\n", texte)[:4000]


class UnjobnetScraper(BaseScraper):
    source_key = "unjobnet"
    nom = "UNjobnet"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_jobs(seen_ids, complet=complet)
