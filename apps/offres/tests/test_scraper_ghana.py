"""Tests du decoupage de GHANEPS (Ghana).

Sans reseau ni dependance : `python test_ghana.py`.

Deux pieges constates le 14/09/2026 :

  - les dates de la liste sont au format Java ("Mon Sep 28 10:00:00 GMT
    2026"), pas en ISO ;
  - la fiche repete le titre dans "Description" pour la plupart des avis :
    la description ne doit pas etre dupliquee.
"""

from apps.offres.scrapers import ghana as g

ENTETE = ("<tr><th>#</th><th>Tender Title</th><th>Procuring Entity</th><th>Info</th>"
          "<th>Bids Submission Deadline</th><th>Procedure</th><th>Status</th>"
          "<th>Notice PDF</th><th>Publication Date</th></tr>")


def ligne(n, rid, titre, entite, echeance, procedure, publie):
    return (f'<tr><td>{n}</td><td><a href="/epps/cft/prepareViewCfTWS.do?resourceId={rid}">{titre}</a></td>'
            f'<td>{entite}</td><td><img alt="Description"/></td><td>{echeance}</td><td>{procedure}</td>'
            f'<td>Bid Submission</td><td></td><td>{publie}</td></tr>')


def page(*lignes):
    return f'<table id="T01">{ENTETE}{"".join(lignes)}</table>'


def fiche(**champs):
    return "<dl>" + "".join(f"<dt>{k}:</dt><dd>{v}</dd>" for k, v in champs.items()) + "</dl>"


def test_dates_java():
    assert g.date_iso("Mon Sep 28 10:00:00 GMT 2026") == "2026-09-28"
    assert g.date_iso("Tue Oct 7 09:00:00 GMT 2026") == "2026-10-07"
    assert g.date_iso("") == "" and g.date_iso("28/09/2026") == ""


def test_decoupe():
    html = page(ligne(1, 3561672, "TABLES", "NKWANTA", "Mon Sep 28 10:00:00 GMT 2026",
                      "National Competitive Tendering", "Mon Sep 14 07:21:37 GMT 2026"),
                ligne(2, 3561729, "CHAIRS", "NKWANTA", "Mon Sep 28 09:00:00 GMT 2026",
                      "National Competitive Tendering", "Mon Sep 14 07:18:45 GMT 2026"))
    assert len(g.lignes_du_tableau(html)) == 2
    assert g.lignes_du_tableau("<table id='autre'><tr><td>x</td></tr></table>") == []


def test_normalisation_sans_fiche():
    cellules = g.lignes_du_tableau(page(ligne(1, 3561672, "TABLES", "NKWANTA",
                                              "Mon Sep 28 10:00:00 GMT 2026",
                                              "National Competitive Tendering",
                                              "Mon Sep 14 07:21:37 GMT 2026")))[0]
    item = g.normalize(cellules, {})
    assert item["id"] == "gh-3561672"
    assert item["source"] == "ghana" and item["pays"] == "Ghana"
    assert item["organisation"] == "NKWANTA"
    assert item["date_limite"] == "2026-09-28" and item["date_publication"] == "2026-09-14"
    assert item["description"] == "Method National Competitive Tendering", item["description"]
    assert item["lien"].endswith("resourceId=3561672")


def test_fiche_enrichit_sans_repeter_le_titre():
    champs = g.champs_de_la_fiche(fiche(**{"Tender Title": "TABLES", "Description": "TABLES",
                                          "Procurement Type": "Goods",
                                          "Procurement Method": "National Competitive Tendering",
                                          "UNSPSC Codes": "56000000-Furniture",
                                          "Bid Security Amount\xa0(GHS)": "2"}))
    assert champs["Bid Security Amount (GHS)"] == "2", "l'espace insecable doit etre normalise"
    cellules = g.lignes_du_tableau(page(ligne(1, 1, "TABLES", "E", "Mon Sep 28 10:00:00 GMT 2026",
                                              "NCT", "Mon Sep 14 07:21:37 GMT 2026")))[0]
    item = g.normalize(cellules, champs)
    assert item["description"] == ("Type Goods. Method National Competitive Tendering. "
                                   "UNSPSC 56000000-Furniture"), item["description"]


def test_description_distincte_est_reprise():
    champs = {"Description": "Supply of 200 desktop computers", "Procurement Type": "Goods"}
    cellules = g.lignes_du_tableau(page(ligne(1, 1, "IT EQUIPMENT", "E", "Mon Sep 28 10:00:00 GMT 2026",
                                              "NCT", "Mon Sep 14 07:21:37 GMT 2026")))[0]
    assert g.normalize(cellules, champs)["description"].startswith("Supply of 200 desktop")


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
