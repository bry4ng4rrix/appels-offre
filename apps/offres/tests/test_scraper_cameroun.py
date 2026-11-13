"""Tests du decoupage du portail camerounais (ARMP).

Sans reseau ni dependance : `python test_cameroun.py`.

Trois pieges constates sur les pages du 14/09/2026 sont couverts :

  - la date de cloture d'un communique vaut 01-01-1970 (epoch rendue comme
    une date) : elle ne doit pas devenir une echeance ;
  - la colonne "Type" d'une liste repete le filtre parcouru, pas la nature
    de l'avis : c'est le code du lien de la fiche qui fait foi ;
  - l'intitule complet est dans l'attribut title du <strong>, le texte
    visible etant tronque par la mise en page.
"""

from apps.offres.scrapers import cameroun as c


def entree(code, ident, titre, mo="MAIRIE", cloture="24-09-2026",
           publie="07-09-2026 10:00:00"):
    """Fabrique un bloc de liste au format exact du portail."""
    return f'''
    <div class="col-md-10 col-12">
      <div class="text-left line-clamp">
        <strong class="text-uppercase" title="{titre}">{titre[:20]}...</strong>
      </div>
      <div class="row mt-4 pr-3">
        <div class="col-md-6 col-12 d-table px-0">
          <div class="d-table-row"><div class="d-table-cell font-weight-bold">MO/AC:</div><div class="d-table-cell">{mo}</div></div>
          <div class="d-table-row"><div class="d-table-cell font-weight-bold">Type:</div><div class="d-table-cell">Appels d'Offres International</div></div>
          <div class="d-table-row"><div class="d-table-cell font-weight-bold">Région :</div><div class="d-table-cell">LITTORAL</div></div>
          <div class="d-table-row"><div class="d-table-cell font-weight-bold">Montant :</div><div class="d-table-cell armp-color-red">1 000 000 FCFA</div></div>
        </div>
        <div class="col-md-5 col-12 d-table">
          <div class="d-table-row armp-color-green"><div class="d-table-cell">Publié le :</div><div class="d-table-cell">{publie}</div></div>
          <div class="d-table-row armp-color-red"><div class="d-table-cell">Date de clôture :</div><div class="d-none">{cloture}</div></div>
        </div>
        <div class="col-md-1 col-12 text-center">
          <a class="btn avis-link" href="/details?type_publication={code}&amp;id_publication={ident}" role="button">Détails</a>
        </div>
      </div>
    </div>'''


def fiche(rubriques):
    blocs = "".join(
        f'<div class="my-1 row"><div class="my-1 font-weight-bolder w-100">'
        f'<strong> {n}.{libelle} <span class="badge d-none">New(Additif)</span></strong></div>'
        f'<div class="my-1 w-100"><p>{texte}</p></div></div>'
        for n, (libelle, texte) in enumerate(rubriques, start=1))
    return f"<html><body><div class='my-4'>{blocs}</div></body></html>"


def test_decoupe_une_page_de_liste():
    html = entree("AO", "64895", "APPEL D'OFFRES INTERNATIONAL N 009") + \
        entree("AMI", "6596", "AVIS DE SOLLICITATION", cloture="24-09-2026")
    avis = c.entrees_de_la_page(html)
    assert len(avis) == 2, f"2 avis attendus, {len(avis)} lus"
    assert avis[0]["type_publication"] == "AO" and avis[0]["id_publication"] == "64895"
    assert avis[0]["MO/AC"] == "MAIRIE"
    assert avis[0]["Date de clôture"] == "24-09-2026"


def test_intitule_complet_vient_de_l_attribut_title():
    titre = "AVIS D'APPEL D'OFFRES NATIONAL OUVERT N 10A/AONO/R-CE/D-NK/C-BONDJOCK"
    avis = c.entrees_de_la_page(entree("AO", "1", titre))
    assert avis[0]["titre"] == titre, avis[0]["titre"]


def test_epoch_n_est_pas_une_echeance():
    assert c.date_iso("01-01-1970") == ""
    assert c.date_iso("") == ""
    assert c.date_iso("09-09-2026 15:59:49") == "2026-09-09"
    assert c.date_iso("31-02-2026") == "", "une date impossible doit rendre vide"


def test_nature_vient_du_code_de_la_fiche():
    brut = c.entrees_de_la_page(entree("AMI", "7", "AVIS"))[0]
    item = c.normalize(brut, {})
    assert item["description"].startswith("Manifestation d'interet"), item["description"]
    assert "International" not in item["description"], \
        "le libelle du filtre ne doit pas etre repris"


def test_normalisation_complete():
    brut = c.entrees_de_la_page(entree("AO", "64895", "APPEL D'OFFRES", mo="CAMTEL"))[0]
    item = c.normalize(brut, {"objet": "Fourniture de materiel",
                              "participation et origine": "Ouverte aux entreprises etrangeres"})
    assert item["id"] == "cm-ao-64895"
    assert item["source"] == "cameroun" and item["pays"] == "Cameroun"
    assert item["organisation"] == "CAMTEL"
    assert item["date_limite"] == "2026-09-24"
    assert item["date_publication"] == "2026-09-07"
    assert "Objet : Fourniture de materiel" in item["description"]
    assert "Participation et origine : Ouverte" in item["description"]
    assert item["lien"].endswith("type_publication=AO&id_publication=64895")


def test_rubriques_de_la_fiche():
    html = fiche([("Objet", "Travaux de rehabilitation"),
                  ("Consistance des prestations", "Terrassement"),
                  ("Cout Prévisionnel", "10 000 000 FCFA"),
                  ("Participation et origine", "Nationales uniquement")])
    r = c.rubriques_de_la_fiche(html)
    assert r["objet"] == "Travaux de rehabilitation", r
    assert r["participation et origine"] == "Nationales uniquement"
    assert "cout prévisionnel" in r


def test_entree_sans_lien_est_ignoree():
    html = entree("AO", "1", "AVIS").replace('href="/details?type_publication=AO&amp;id_publication=1"', 'href="#"')
    assert c.entrees_de_la_page(html) == []


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
