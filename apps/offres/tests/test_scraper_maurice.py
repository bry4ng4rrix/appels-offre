"""Tests du decoupage de la page des marches publics mauriciens.

Sans reseau ni dependance : `python test_maurice.py`.

Le portail rend ses avis en <div class="row"> de huit colonnes. Trois pieges
constates sur la page du 25/08/2026 sont couverts ici :

  - l'heure de cloture s'ecrit tantot "14:00", tantot "13.30", et manque
    parfois tout a fait ;
  - un avis sur vingt ne porte aucune reference de marche ;
  - un avis sur vingt ne joint aucun document, donc aucun lien.

Le quatrieme cas -- une mise en page qui changerait -- n'a pas ete constate
mais couterait cher : lire la date de cloture dans la colonne de la categorie
produirait des verdicts silencieusement faux. D'ou le refus des lignes qui ne
presentent pas huit colonnes.
"""

from apps.offres.scrapers import maurice as m

ENTETE = (
    '<div class="row" style="background-color:#192a3d;">'
    '<div class="col-sm-2" style="a">Public Body</div>'
    '<div class="col-sm-2" style="a">Procurement Ref No.</div>'
    '<div class="col-sm-1" style="a">Procurement category</div>'
    '<div class="col-sm-2" style="a">Procurement description</div>'
    '<div class="col-sm-1" style="a">Closing date/time</div>'
    '<div class="col-sm-1" style="a">Detailed Procurement Notice</div>'
    '<div class="col-sm-1" style="a">Bidding document</div>'
    '<div class="col-sm-1" style="a">Addendum</div>'
)


def ligne(organisme, ref, categorie, description, cloture, lien=None):
    """Fabrique un bloc d'avis au format exact du portail."""
    doc = (f"<a href='{lien}' target='_blank'>Download Procurement Notice</a>"
           if lien else "")
    return (
        '<div class="row" style="b">'
        f'<div class="col-sm-2" style="a">{organisme}</div>'
        f'<div class="col-sm-2" style="a">{ref}</div>'
        f'<div class="col-sm-1" style="a">{categorie}</div>'
        f'<div class="col-sm-2" style="a">{description}</div>'
        f'<div class="col-sm-1" style="a">{cloture}</div>'
        f'<div class="col-sm-1" style="a">{doc}</div>'
        '<div class="col-sm-1" style="a"></div>'
        '<div class="col-sm-1" style="a"></div>'
    )


INFORMATIQUE = ligne(
    "Mauritius Tourism Promotion Authority", "MTPA/IFB/3/ 2026-27",
    "Other services",
    "Invitation of Bids for Design, Supply, Installation, Configuration, "
    "Testing and Commissioning of a modern, secure and scalable IT "
    "Infrastructure Environment including Retrofit",
    "3 September 2026 12.00",
    "/publicprocurement/wp-content/uploads/2026/08/IFB-Revamping-1.docx")

SANS_REFERENCE = ligne(
    "Higher Education Commission", "", "Other services",
    "CALL FOR EXPRESSIONS OF INTEREST FOR REGISTRATION OF SUPPLIERS",
    "21 September 2026",
    "/publicprocurement/wp-content/uploads/2026/08/Notice.pdf")

SANS_LIEN = ligne(
    "Ministry of Environment", "ENV/26-27/Q16/RFP/ONB", "Other services",
    "Provision of the Services for One Project Assistant under the Expert "
    "Skills Scheme for ISLANDS Project - Relaunch",
    "10 September 2026 13.30")

PAGE = ENTETE + INFORMATIQUE + SANS_REFERENCE + SANS_LIEN


def avis_de(page):
    return [m.normalize(cols, bloc) for cols, bloc in m.lignes_de_la_page(page)]


def test_l_entete_n_est_pas_un_avis():
    assert len(m.lignes_de_la_page(PAGE)) == 3, "l'en-tete a ete comptee"
    assert all("Public Body" != a["organisation"] for a in avis_de(PAGE))


def test_les_trois_ecritures_de_l_heure():
    """"14:00", "13.30" et l'absence d'heure donnent toutes une date."""
    assert m.date_cloture("22 September 2026 14:00") == "2026-09-22"
    assert m.date_cloture("10 September 2026 13.30") == "2026-09-10"
    assert m.date_cloture("21 September 2026") == "2026-09-21"
    assert m.date_cloture("3 September 2026 12.00") == "2026-09-03"
    assert m.date_cloture("01 October 2026 10:30") == "2026-10-01"


def test_une_date_illisible_ne_fait_pas_tomber_la_collecte():
    """Sans date, l'avis reste collecte : le pipeline accepte le champ vide."""
    assert m.date_cloture("") == ""
    assert m.date_cloture("a confirmer") == ""
    assert m.date_cloture("31 Fevrier 2026 10:00") == "", "mois francais"
    assert m.date_cloture("30 February 2026 10:00") == "", "date inexistante"


def test_un_avis_sans_reference_recoit_un_identifiant():
    avis = avis_de(SANS_REFERENCE)[0]
    assert avis["id"].startswith("maurice-")
    assert len(avis["id"]) > len("maurice-")


def test_un_avis_sans_lien_pointe_vers_le_portail():
    """Faute de document joint, le lien mene a la page qui liste l'avis."""
    avis = avis_de(SANS_LIEN)[0]
    assert avis["lien"] == m.MAURICE_URL


def test_les_liens_relatifs_deviennent_absolus():
    avis = avis_de(INFORMATIQUE)[0]
    assert avis["lien"].startswith("https://publicprocurement.govmu.org/")
    assert avis["lien"].endswith("IFB-Revamping-1.docx")


def test_deux_avis_distincts_ont_deux_identifiants():
    ids = {a["id"] for a in avis_de(PAGE)}
    assert len(ids) == 3, f"collision d'identifiants : {ids}"


def test_l_identifiant_est_stable_d_un_run_a_l_autre():
    """Sans quoi chaque collecte reremonterait toute la page comme neuve."""
    assert avis_de(PAGE)[0]["id"] == avis_de(PAGE)[0]["id"]
    assert m.identifiant("REF/1", "objet") == m.identifiant("REF/1", "objet")
    assert m.identifiant("REF/1", "objet") != m.identifiant("REF/2", "objet")


def test_le_titre_porte_l_objet_du_marche():
    """Le portail ne publie pas de titre : la description en tient lieu.

    La tronquer priverait le tri de sa seule matiere -- c'est ce qui avait
    ramene 0 retenue sur 4 quand les titres de Madagascar National Parks
    etaient jugés sans description.
    """
    avis = avis_de(INFORMATIQUE)[0]
    assert "IT Infrastructure Environment" in avis["titre"]
    assert avis["pays"] == "Maurice"
    assert "MTPA/IFB/3/ 2026-27" in avis["description"]


def test_une_ligne_amputee_est_refusee():
    """Mieux vaut perdre une ligne que lire un champ pour un autre."""
    tronquee = ('<div class="row" style="b">'
                '<div class="col-sm-2" style="a">Ministry</div>'
                '<div class="col-sm-1" style="a">10 September 2026</div>')
    assert m.lignes_de_la_page(tronquee) == []
    # La page complete, elle, reste lue en entier.
    assert len(m.lignes_de_la_page(PAGE + tronquee)) == 3


def test_les_avis_deja_vus_ne_reviennent_pas(monkey=None):
    """Le dedoublonnage s'appuie sur les identifiants deja en base."""
    connus = {avis_de(PAGE)[0]["id"]}
    reste = [a for a in avis_de(PAGE) if a["id"] not in connus]
    assert len(reste) == 2


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
