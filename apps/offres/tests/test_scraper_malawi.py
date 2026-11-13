"""Tests du decoupage de la page des avis du Malawi (PPDA).

Sans reseau ni dependance : `python test_malawi.py`.
"""

from apps.offres.scrapers import malawi as m

ENTETE = ("<tr><th>Title</th><th>Institution</th><th>Reference No.</th>"
          "<th>Publish Date</th><th>Closing Date</th><th>Attachment</th></tr>")


def ligne(titre, institution, ref, publie, cloture, pdf=None):
    a = f'<a class="btn" href="https://ppda.mw/storage/documents/opentenders/{pdf}"><i class="fa fa-download"></i></a>' if pdf else ""
    return (f"<tr><td> {titre}</td><td> {institution}</td><td> {ref}</td>"
            f"<td> {publie}</td><td> {cloture}</td><td class=\"d-flex\">{a}</td></tr>")


def page(*lignes):
    return f'<table id="tenderstable" class="table">{ENTETE}{"".join(lignes)}</table>'


def test_decoupe():
    html = page(ligne("MEDICAL EQUIPMENT1", "Mangochi", "MHDC/1", "2026-09-14", "2026-09-18", "RFQ A.pdf"),
                ligne("MEDICAL EQUIPMENT2", "Mangochi", "MHDC/2", "2026-09-14", "2026-09-18"))
    assert len(m.lignes_du_tableau(html)) == 2
    assert m.lignes_du_tableau("<table><tr><td>x</td></tr></table>") == []


def test_le_nom_du_pdf_decrit_le_marche():
    cellules = m.lignes_du_tableau(page(ligne(
        "MEDICAL EQUIPMENT1", "Mangochi District Council", "MHDC/RCDF/2026/27",
        "2026-09-14", "2026-09-18",
        "RFQ Health RCDF - Supply of CSSD and Emergency Treatment Equipment.pdf")))[0]
    item = m.normalize(cellules)
    assert item["description"] == ("Reference MHDC/RCDF/2026/27. RFQ Health RCDF - Supply of CSSD "
                                   "and Emergency Treatment Equipment. MEDICAL EQUIPMENT1"), item["description"]
    assert item["lien"].endswith("Equipment.pdf")
    assert item["date_limite"] == "2026-09-18" and item["date_publication"] == "2026-09-14"
    assert item["organisation"] == "Mangochi District Council"
    assert item["source"] == "malawi" and item["pays"] == "Malawi"


def test_pdf_homonyme_du_titre_n_est_pas_repete():
    cellules = m.lignes_du_tableau(page(ligne("NKHATABAY PRISON RFQ", "MPS", "R/1",
                                              "2026-09-12", "2026-09-16", "NKHATABAY PRISON RFQ.pdf")))[0]
    assert m.normalize(cellules)["description"] == "Reference R/1. NKHATABAY PRISON RFQ"


def test_identifiant_distingue_deux_lots_de_meme_reference():
    a = m.normalize(m.lignes_du_tableau(page(ligne("LOT 1", "X", "REF", "2026-09-01", "2026-09-16")))[0])
    b = m.normalize(m.lignes_du_tableau(page(ligne("LOT 2", "X", "REF", "2026-09-01", "2026-09-16")))[0])
    c = m.normalize(m.lignes_du_tableau(page(ligne("LOT 1", "X", "REF", "2026-09-01", "2026-09-16")))[0])
    assert a["id"] != b["id"] and a["id"] == c["id"]
    assert a["lien"] == m.MW_URL, "sans piece jointe, le lien est la page de la liste"


def test_nom_de_piece_decode_les_espaces():
    assert m.nom_de_la_piece("https://x/y/RFQ%20WELDING%20MATERIALS.pdf") == "RFQ WELDING MATERIALS"
    assert m.nom_de_la_piece("") == ""


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
