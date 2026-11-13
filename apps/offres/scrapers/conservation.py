"""Appels d'offres de Conservation International.

Source : https://www.conservation.org/procurement-opportunities

ONG environnementale presente a Madagascar, qui publie ses consultations pour
prestataires et consultants externes.

Constate le 25/08/2026 :

  - robots.txt porte "Allow: /", et les conditions d'utilisation -- lues en
    entier -- n'interdisent ni la collecte automatisee, ni les robots, ni
    l'extraction. C'est le cadre le plus net du pipeline apres TED.

  - La page ne liste que les avis OUVERTS, sans pagination ni archive. Une
    seule requete suffit, et un avis disparait a sa cloture.

  - Le site est un Next.js servi par Sanity. Les avis sont des <article> dans
    une section `m-outer-rfpList`, chacun portant un titre, une date de
    parution, une date limite et un lien -- vers une fiche HTML ou, plus
    souvent, directement vers le PDF de l'appel d'offres.

Aucune description n'est publiee, meme sur les fiches HTML : l'objet du marche
vit dans le document joint. Le module va donc l'y chercher.

Ce detour n'est pas un confort. Mesure du 25/08/2026 : l'appel d'offres
"Biodiversity Hotspots Global Platform" -- conception et developpement d'une
plateforme web, exactement notre metier -- etait ECARTE par le tri quand il ne
recevait que son titre, et RETENU des que la description reelle
l'accompagnait. Le pays et la longueur du titre n'y changeaient rien : les
trois variantes sans description ont toutes ete ecartees. Sans lecture du
document, cette source rejette ses meilleures offres.
"""

import hashlib
import io
import re
from datetime import date
from html import unescape

from .base import BaseScraper
from .http import get, get_html
from Offre.sources import CONSERVATION_URL, CONSERVATION_BASE, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "text/html"}

#: Pages du document lues pour en tirer une description. L'objet du marche
#: figure toujours dans les premieres ; aller plus loin ne rapporte que des
#: annexes juridiques et coute du temps.
PDF_MAX_PAGES = 3

#: Longueur conservee en base. Le tri n'en envoie que LLM_DESCRIPTION_MAX au
#: modele, mais le rapport affiche le reste.
EXTRAIT_MAX = 700

#: Phrases par lesquelles ces appels d'offres annoncent leur objet. Le debut
#: du document, lui, n'est que l'en-tete de l'entite contractante.
#:
#: L'ORDRE COMPTE : la premiere amorce trouvee l'emporte, et elles ne se
#: valent pas. "Description of the project" ouvre sur l'objet reel du marche ;
#: "is issuing a Request for Proposals for the procurement described below"
#: n'est qu'une formule contractuelle qui ne dit rien de ce qui est achete.
#: Les plus informatives passent donc en premier, les formules generiques ne
#: servant que de dernier recours.
AMORCES = (
    "description of the project", "objet du marche", "scope of work",
    "seeks a", "seeks to", "is seeking", "is soliciting",
    "invites all eligible", "invites qualified", "is issuing",
)

#: Lieux reconnus, du plus long au plus court a l'usage : "Republique
#: democratique du Congo" doit gagner sur "Congo", et "Papua New Guinea" sur
#: "Guinea". La valeur est l'etiquette francaise stockee en base.
#:
#: La liste n'est pas mondiale et n'a pas a l'etre : elle couvre les pays ou
#: Conservation International intervient, plus les lieux effectivement
#: rencontres dans leurs avis. Un lieu inconnu laisse simplement le champ a
#: "International", ce qui est vrai faute de mieux.
LIEUX = {
    "democratic republic of the congo": "Republique democratique du Congo",
    "republique democratique du congo": "Republique democratique du Congo",
    "cote d'ivoire": "Cote d'Ivoire", "ivory coast": "Cote d'Ivoire",
    "south africa": "Afrique du Sud", "afrique du sud": "Afrique du Sud",
    "sierra leone": "Sierra Leone", "burkina faso": "Burkina Faso",
    "new caledonia": "Nouvelle-Caledonie", "costa rica": "Costa Rica",
    "madagascar": "Madagascar", "mozambique": "Mozambique",
    "botswana": "Botswana", "tanzania": "Tanzanie", "tanzanie": "Tanzanie",
    "namibia": "Namibie", "zimbabwe": "Zimbabwe", "zambia": "Zambie",
    "ethiopia": "Ethiopie", "cameroon": "Cameroun", "cameroun": "Cameroun",
    "senegal": "Senegal", "liberia": "Liberia", "rwanda": "Rwanda",
    "uganda": "Ouganda", "malawi": "Malawi", "eswatini": "Eswatini",
    "angola": "Angola", "kenya": "Kenya", "ghana": "Ghana", "gabon": "Gabon",
    "guinea": "Guinee", "hawaii": "Hawai (Etats-Unis)",
    "hawai": "Hawai (Etats-Unis)", "indonesia": "Indonesie",
    "philippines": "Philippines", "colombia": "Colombie", "brazil": "Bresil",
    "peru": "Perou", "guyana": "Guyana", "suriname": "Suriname",
    "cambodia": "Cambodge", "india": "Inde", "fiji": "Fidji",
    "samoa": "Samoa", "timor": "Timor-Leste", "mexico": "Mexique",
}

#: Pays d'Afrique de la table ci-dessus. Sert au marquage regional : le
#: rapport et l'interface peuvent ainsi isoler l'Afrique sans reconstruire
#: la correspondance.
AFRIQUE = {
    "Republique democratique du Congo", "Cote d'Ivoire", "Afrique du Sud",
    "Sierra Leone", "Burkina Faso", "Madagascar", "Mozambique", "Botswana",
    "Tanzanie", "Namibie", "Zimbabwe", "Zambie", "Ethiopie", "Cameroun",
    "Senegal", "Liberia", "Rwanda", "Ouganda", "Malawi", "Eswatini",
    "Angola", "Kenya", "Ghana", "Gabon", "Guinee",
}

#: Section qui contient la liste. Ancrage volontairement semantique : les
#: <article> portent des classes Tailwind ("flex flex-col gap-6") qui ne
#: survivent pas a un changement de mise en page.
SECTION = "m-outer-rfpList"


def texte_brut(html: str) -> str:
    """Retire balises et entites d'un fragment.

    React seme des marqueurs de commentaire vides au milieu des textes --
    "Posting Date<!-- -->: <!-- -->2026-08-24" -- qu'il faut retirer avant de
    lire quoi que ce soit.
    """
    sans_commentaires = re.sub(r"<!--.*?-->", "", html or "")
    sans_balises = re.sub(r"<[^>]+>", " ", sans_commentaires)
    return re.sub(r"\s+", " ", unescape(sans_balises)).strip()


def champ_date(bloc: str, libelle: str) -> str:
    """Lit "Due Date : 2026-08-31" -> "2026-08-31". Vide si absent.

    Le format est deja ISO : aucune table de mois n'est necessaire, contrairement
    aux sources francaises ou anglaises en toutes lettres.
    """
    m = re.search(rf"{libelle}\s*:?\s*(\d{{4}}-\d{{2}}-\d{{2}})",
                  texte_brut(bloc), re.I)
    if not m:
        return ""
    try:
        return date.fromisoformat(m.group(1)).isoformat()
    except ValueError:
        return ""


def identifiant(titre: str) -> str:
    """Identifiant stable, derive du titre.

    Le lien serait le candidat naturel, mais il ne convient pas : deux avis
    sur trois pointent vers un PDF de Sanity dont le nom est le condense du
    fichier. Republier le PDF avec une virgule corrigee change ce nom, et
    l'avis reviendrait comme neuf a chaque retouche.

    Le titre, lui, bouge rarement. Le risque assume est symetrique -- une
    correction de titre cree un doublon -- mais il se produit moins souvent.
    """
    graine = (titre or "").strip().lower().encode("utf-8")
    return "conservation-" + hashlib.sha1(graine).hexdigest()[:12]


def lien_absolu(bloc: str) -> str:
    """Premier lien de l'annonce, absolu. La page elle-meme a defaut."""
    m = re.search(r'href="([^"]+)"', bloc)
    if not m:
        return CONSERVATION_URL
    lien = m.group(1)
    if lien.startswith("http"):
        return lien
    return CONSERVATION_BASE + (lien if lien.startswith("/") else "/" + lien)


def lien_document(lien: str) -> str:
    """URL du PDF decrivant le marche, ou chaine vide.

    Trois formes coexistent sur ce site :
      - un PDF servi directement par Sanity ;
      - un .docx, que l'on ne sait pas lire et que l'on ignore ;
      - une fiche /rfp/, dont les pieces jointes vivent ailleurs sur Sanity,
        sous /media-libraries/ et non sous /files/.
    """
    if lien.lower().endswith(".pdf"):
        return lien
    if "/rfp/" not in lien:
        return ""

    try:
        page = get_html(lien, HEADERS, timeout=45)
    except Exception:
        return ""

    # Le payload Next.js echappe les URL : la contre-oblique est exclue de la
    # classe, sans quoi elle serait avalee dans l'URL.
    liens = re.findall(
        r'https://cdn\.sanity\.io/(?:files|media-libraries)/[^"\\ ]+?\.pdf', page)
    if not liens:
        return ""
    # Une fiche joint parfois plusieurs documents : plans, clarifications,
    # budget. Celui qui porte l'appel d'offres prime.
    for motif in ("request-for-proposal", "rfp", "rfq"):
        for u in liens:
            if motif in u.lower() and "clarification" not in u.lower():
                return u
    return liens[0]


def extrait_du_document(url: str) -> str:
    """Premieres phrases utiles du document, ou chaine vide.

    Sans cet extrait la source ne sert a rien : mesure faite le 25/08/2026,
    l'appel d'offres "Biodiversity Hotspots Global Platform" -- conception et
    developpement d'une plateforme web, exactement notre metier -- etait
    ECARTE par le tri quand il ne recevait que le titre, et RETENU des que la
    description reelle l'accompagnait. Le titre seul ne suffit pas.

    Toute defaillance est silencieuse et sans consequence : l'offre garde sa
    description minimale et reste collectee.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reponse = get(url, HEADERS, timeout=90)
        pages = PdfReader(io.BytesIO(reponse.content)).pages[:PDF_MAX_PAGES]
        texte = re.sub(r"\s+", " ", " ".join((p.extract_text() or "") for p in pages))
    except Exception:
        return ""

    if not texte.strip():
        return ""

    # On saute l'en-tete contractuel pour atteindre l'objet du marche.
    minuscules = texte.lower()
    depart = 0
    for amorce in AMORCES:
        trouve = minuscules.find(amorce)
        if trouve != -1:
            depart = trouve
            break
    return texte[depart:depart + EXTRAIT_MAX].strip()


def lieu(titre: str, description: str) -> str:
    """Pays d'execution, deduit du titre puis du document. "International" a defaut.

    Le TITRE prime sur la description : il enonce l'objet du marche, tandis
    qu'un document de vingt pages cite des pays au fil de ses annexes -- une
    clause de reglement des differends, la liste des bureaux de l'ONG. Chercher
    d'abord dans le titre evite de situer en Suisse un marche angolais.

    Les cles sont essayees de la plus longue a la plus courte, pour que
    "Democratic Republic of the Congo" gagne sur "Congo".
    """
    ordonnees = sorted(LIEUX, key=len, reverse=True)
    for source in (titre or "", description or ""):
        minuscule = source.lower()
        for cle in ordonnees:
            if re.search(r"\b" + re.escape(cle), minuscule):
                return LIEUX[cle]
    return "International"


def normalize(bloc: str) -> dict:
    """Ramene un avis au format commun aux autres sources."""
    titre_html = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", bloc, re.S)
    titre = texte_brut(titre_html.group(1)) if titre_html else ""
    parution = champ_date(bloc, "Posting Date")
    echeance = champ_date(bloc, "Due Date")

    details = []
    if parution:
        details.append(f"Paru le {parution}")
    details.append("Appel d'offres Conservation International")
    # Le detail n'est pas publie en HTML : on dit ou il se trouve plutot que
    # de laisser le champ vide.
    details.append("Cahier des charges dans le document joint")

    return {
        "id": identifiant(titre),
        "source": "conservation",
        "titre": titre,
        "organisation": "Conservation International",
        # Renseigne apres lecture du document : la liste HTML ne porte aucun
        # lieu. Reste "International" tant que rien n'est reconnu.
        "pays": lieu(titre, ""),
        "date_limite": echeance,
        "description": ". ".join(details),
        "lien": lien_absolu(bloc),
    }


def blocs_de_la_page(html: str) -> list:
    """Decoupe la page en annonces.

    On restreint d'abord a la section de la liste : le reste de la page porte
    d'autres <article> -- articles de blog, encarts -- qui ne sont pas des
    appels d'offres.
    """
    compact = re.sub(r"\s+", " ", html or "")
    debut = compact.find(SECTION)
    if debut == -1:
        return []
    zone = compact[debut:]
    return [b for b in re.findall(r"<article[^>]*>(.*?)</article>", zone)
            if "Due Date" in b]


def est_ouvert(item: dict) -> bool:
    """La page n'annonce que des avis ouverts, mais on verifie.

    Un avis sans date limite lisible est conserve : on ne peut pas affirmer
    qu'il est clos.
    """
    if not item["date_limite"]:
        return True
    return date.fromisoformat(item["date_limite"]) >= date.today()


def scrape_new_avis(seen_ids: set, complet: bool = False) -> list:
    """Collecte les avis inconnus encore ouverts."""
    nouveaux = []
    vus_ce_run = set()
    clos = 0
    limite = None if complet else (FIRST_RUN_MAX_ITEMS if not seen_ids else None)

    try:
        html = get_html(CONSERVATION_URL, HEADERS, timeout=45)
    except Exception as exc:
        print(f"Conservation International : page inaccessible ({str(exc)[:70]}).")
        return []

    blocs = blocs_de_la_page(html)
    if not blocs:
        # Le site repond mais nous ne reconnaissons plus sa mise en page :
        # le dire vaut mieux que de rendre zero en silence.
        print("Conservation International : aucun avis reconnu, "
              "la mise en page a peut-etre change.")
        return []

    for bloc in blocs:
        item = normalize(bloc)
        if not item["titre"] or item["id"] in seen_ids or item["id"] in vus_ce_run:
            continue
        if not complet and not est_ouvert(item):
            clos += 1
            continue
        # L'objet du marche n'existe que dans le document joint : sans lui,
        # le tri juge sur le seul titre et ecarte des offres pertinentes.
        document = lien_document(item["lien"])
        if document:
            extrait = extrait_du_document(document)
            if extrait:
                item["description"] = item["description"] + ". " + extrait
                # Le lieu se lit souvent dans le document, jamais dans la liste.
                item["pays"] = lieu(item["titre"], extrait)
                if item["pays"] in AFRIQUE:
                    item["description"] += " (Afrique)"

        vus_ce_run.add(item["id"])
        nouveaux.append(item)
        if limite is not None and len(nouveaux) >= limite:
            print(f"Conservation International : plafond premier lancement "
                  f"atteint ({limite} avis).")
            break

    if clos:
        print(f"  Conservation International : {clos} avis deja clos ecarte(s).")
    return nouveaux


class ConservationScraper(BaseScraper):
    source_key = "conservation"
    nom = "Conservation International"

    def scrape(self, seen_ids, complet=False):
        return scrape_new_avis(seen_ids, complet=complet)
