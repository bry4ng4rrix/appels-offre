"""Tests du decoupage de la page de Conservation International.

Sans reseau ni dependance : `python test_conservation.py`.

Quatre particularites de cette source sont couvertes ici :

  - React seme des marqueurs de commentaire vides au milieu des textes :
    "Posting Date<!-- -->: <!-- -->2026-08-24". Les lire naivement rend une
    date introuvable.
  - La page porte d'autres <article> que les appels d'offres -- encarts,
    articles de blog. Seule la section `m-outer-rfpList` compte.
  - Les <article> ne portent que des classes Tailwind ("flex flex-col gap-6"),
    qui ne survivraient pas a un changement de mise en page. Le decoupage
    s'ancre donc sur la section, pas sur elles.
  - L'objet du marche n'est publie nulle part en HTML : il faut aller le lire
    dans le document joint, dont la resolution a ses propres pieges.
"""

from datetime import date, timedelta

from apps.offres.scrapers import conservation as c

FUTUR = (date.today() + timedelta(days=20)).isoformat()
PASSE = (date.today() - timedelta(days=5)).isoformat()


def annonce(titre, parution, echeance, lien="https://cdn.sanity.io/files/x/a1b2.pdf"):
    """Fabrique un <article> au format exact du site, marqueurs React compris."""
    return (
        '<article class="flex flex-col gap-6"><div class="space-y-4">'
        f'<h6 class="text-balance font-body" size="60">{titre}</h6><div>'
        f'<p class="text-sm">Posting Date<!-- -->: <!-- -->{parution}</p>'
        f'<p class="text-sm">Due Date<!-- -->: <!-- -->{echeance}</p>'
        f'</div></div><a target="_blank" href="{lien}">'
        '<button class="text-base">VIEW AS PDF</button></a></article>'
    )


WEB = annonce(
    "Biodiversity Hotspots Global Platform: Phase 1 Scoping Exercise and Brand "
    "Development; Optional Phase 2 Website Design, Development and Launch",
    "2026-08-13", FUTUR)

VEHICULES = annonce("Supply of Project Vehicles", "2026-08-24", FUTUR)

CLOS = annonce("NGED019: Livestock medicine", "2026-07-01", PASSE)

FICHE_HTML = annonce("Installation of REEFRAME Modules", "2026-07-24", FUTUR,
                     lien="/rfp/installation-of-reeframe-modules")

#: Un <article> hors de la section de liste : encart editorial du bas de page.
INTRUS = ('<article class="flex flex-col gap-6"><h6>Protecting nature</h6>'
          '<p>Read our latest story</p></article>')

PAGE = (INTRUS + '<section class="m-block--outer m-outer-rfpList">'
        + WEB + VEHICULES + CLOS + FICHE_HTML + '</section>')


def test_l_intrus_hors_liste_est_ignore():
    """Seuls les <article> de la section rfpList sont des appels d'offres."""
    blocs = c.blocs_de_la_page(PAGE)
    assert len(blocs) == 4, f"{len(blocs)} blocs au lieu de 4"
    titres = [c.normalize(b)["titre"] for b in blocs]
    assert "Protecting nature" not in titres


def test_les_marqueurs_react_ne_cachent_pas_les_dates():
    """"Posting Date<!-- -->: <!-- -->2026-08-13" doit se lire."""
    item = c.normalize(WEB)
    assert item["date_limite"] == FUTUR
    assert "Paru le 2026-08-13" in item["description"]


def test_une_date_absente_ou_illisible_ne_fait_pas_tomber_la_collecte():
    assert c.champ_date("<p>Due Date: bientot</p>", "Due Date") == ""
    assert c.champ_date("<p>rien du tout</p>", "Due Date") == ""
    # Une date impossible ne doit pas lever, seulement rendre vide.
    assert c.champ_date("<p>Due Date: 2026-02-30</p>", "Due Date") == ""


def test_un_avis_clos_est_ecarte_mais_pas_un_avis_sans_date():
    assert c.est_ouvert(c.normalize(WEB)) is True
    assert c.est_ouvert(c.normalize(CLOS)) is False
    sans_date = c.normalize(annonce("Sans echeance", "2026-08-01", "a confirmer"))
    assert sans_date["date_limite"] == ""
    assert c.est_ouvert(sans_date) is True, "on ne peut pas l'affirmer clos"


def test_le_lien_relatif_devient_absolu():
    assert c.normalize(FICHE_HTML)["lien"] == (
        "https://www.conservation.org/rfp/installation-of-reeframe-modules")
    assert c.normalize(WEB)["lien"].startswith("https://cdn.sanity.io/")


def test_l_identifiant_tient_au_titre_pas_au_lien():
    """Deux avis sur trois pointent vers un PDF dont le nom est le condense du
    fichier : republier le document changerait l'identifiant, et l'avis
    reviendrait comme neuf a chaque retouche."""
    meme_titre_autre_pdf = annonce(
        "Supply of Project Vehicles", "2026-08-24", FUTUR,
        lien="https://cdn.sanity.io/files/x/ZZZZ-nouvelle-version.pdf")
    assert c.normalize(VEHICULES)["id"] == c.normalize(meme_titre_autre_pdf)["id"]
    assert c.normalize(VEHICULES)["id"] != c.normalize(WEB)["id"]


def test_l_identifiant_est_stable_et_prefixe():
    item = c.normalize(WEB)
    assert item["id"].startswith("conservation-")
    assert item["id"] == c.normalize(WEB)["id"]


def test_le_titre_entier_est_conserve():
    """Le titre porte l'essentiel du signal : le tronquer l'appauvrirait.

    Il ne suffit pourtant pas a lui seul -- voir l'extraction du document
    joint plus bas.
    """
    item = c.normalize(WEB)
    assert "Website Design, Development and Launch" in item["titre"]
    assert item["source"] == "conservation"
    assert item["organisation"] == "Conservation International"


def test_une_page_meconnaissable_ne_rend_pas_zero_en_silence():
    """Sans la section attendue, mieux vaut ne rien rendre que deviner."""
    assert c.blocs_de_la_page("<html><body>refonte du site</body></html>") == []
    assert c.blocs_de_la_page("") == []


# --- Resolution du document joint et extraction ---------------------------

#: Extrait d'une page /rfp/ : plusieurs pieces jointes, dont l'appel d'offres
#: lui-meme, ses clarifications et un tableur de budget. Les URL y sont
#: echappees par Next.js, d'ou les contre-obliques finales.
PAGE_RFP = (
    'x"https://cdn.sanity.io/media-libraries/mlm/files/containers/aaa/'
    'gef-evaluation-budget-template.xlsx\\"'
    'y"https://cdn.sanity.io/media-libraries/mlm/files/containers/bbb/'
    'ci-gef-001-fy27-rfp-mtr-angola-gwp-clarifications.pdf\\"'
    'z"https://cdn.sanity.io/media-libraries/mlm/files/containers/ccc/'
    'ci-gef-001-fy27-rfp-mtr-angola-gwp.pdf\\"'
)


def test_un_lien_pdf_est_pris_tel_quel():
    pdf = "https://cdn.sanity.io/files/x/abc.pdf"
    assert c.lien_document(pdf) == pdf


def test_un_docx_est_ignore():
    """On ne sait pas lire les .docx : mieux vaut aucune description
    qu'un extrait fantaisiste."""
    assert c.lien_document("https://cdn.sanity.io/files/x/abc.docx") == ""


def test_une_fiche_rfp_rend_l_appel_d_offres_pas_ses_annexes():
    """Une fiche joint plans, clarifications et budget : c'est l'appel
    d'offres lui-meme qu'il faut lire."""
    reel = c.get_html
    c.get_html = lambda *a, **k: PAGE_RFP
    try:
        trouve = c.lien_document("https://www.conservation.org/rfp/quelconque")
    finally:
        c.get_html = reel
    assert trouve.endswith("ci-gef-001-fy27-rfp-mtr-angola-gwp.pdf"), trouve
    assert "clarifications" not in trouve
    assert "xlsx" not in trouve
    # La contre-oblique d'echappement ne doit pas rester collee a l'URL.
    assert not trouve.endswith(chr(92))


def test_une_fiche_injoignable_ne_fait_pas_tomber_la_collecte():
    reel = c.get_html
    def tombe(*a, **k):
        raise RuntimeError("503")
    c.get_html = tombe
    try:
        assert c.lien_document("https://www.conservation.org/rfp/quelconque") == ""
    finally:
        c.get_html = reel


def test_l_amorce_la_plus_informative_gagne():
    """L'ordre des amorces compte.

    "is issuing a Request for Proposals for the procurement described below"
    est une formule contractuelle qui ne dit rien de ce qui est achete ;
    "Description of the project" ouvre sur l'objet reel. Trois extraits sur
    cinq tombaient sur la formule avant que l'ordre ne soit corrige.
    """
    amorces = list(c.AMORCES)
    assert amorces.index("description of the project") < amorces.index("is issuing")
    assert amorces.index("scope of work") < amorces.index("invites all eligible")


def test_un_document_illisible_laisse_l_offre_intacte():
    """Aucune defaillance de lecture ne doit perdre une offre."""
    reel = c.get
    def tombe(*a, **k):
        raise RuntimeError("timeout")
    c.get = tombe
    try:
        assert c.extrait_du_document("https://cdn.sanity.io/files/x/abc.pdf") == ""
    finally:
        c.get = reel


# --- Detection du lieu -----------------------------------------------------

def test_le_pays_est_lu_dans_le_titre_puis_dans_le_document():
    assert c.lieu("Midterm Review ... in Angola's Conservation Areas", "") == "Angola"
    assert c.lieu("NGED019: Livestock medicine",
                  "Conservation South Africa (CSA), as a local affiliate") == "Afrique du Sud"


def test_le_titre_prime_sur_le_document():
    """Un document de vingt pages cite des pays dans ses annexes -- clause de
    reglement des differends, liste des bureaux de l'ONG. Chercher d'abord
    dans le titre evite de situer en Inde un marche angolais."""
    assert c.lieu("Projet en Angola", "bureau regional en Inde et au Kenya") == "Angola"


def test_le_plus_long_nom_gagne():
    """Sans cela, "Democratic Republic of the Congo" serait lu comme "Congo",
    et "Papua New Guinea" comme "Guinea"."""
    trouve = c.lieu("Programme in the Democratic Republic of the Congo", "")
    assert trouve == "Republique democratique du Congo", trouve


def test_un_lieu_inconnu_reste_international():
    """Mieux vaut un champ honnete qu'un pays devine."""
    assert c.lieu("Biodiversity Hotspots Global Platform", "") == "International"
    assert c.lieu("", "") == "International"


def test_l_afrique_est_un_sous_ensemble_des_lieux_connus():
    """AFRIQUE sert au marquage regional : toute etiquette qui y figure doit
    pouvoir sortir de lieu(), sinon le marquage ne se declenchera jamais."""
    etiquettes = set(c.LIEUX.values())
    orphelines = c.AFRIQUE - etiquettes
    assert not orphelines, f"etiquettes absentes de LIEUX : {orphelines}"


def test_hawai_n_est_pas_range_en_afrique():
    """Constate sur l'avis REEFRAME : Waikiki, Oahu. Conservation
    International n'est pas une source africaine, et le champ doit le dire."""
    assert c.lieu("Installation of REEFRAME Modules",
                  "offshore of Waikiki, Oahu, Hawaii") not in c.AFRIQUE


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
