"""Tests du decoupage des tableaux de la DGMP du Mali.

Sans reseau ni dependance : `python test_mali.py`.

Deux pieges constates le 14/09/2026 :

  - une ligne sur huit n'a pas de dossier joint, donc pas de numero de
    fichier : elle recoit un identifiant hache ;
  - le lien du dossier est relatif au site ("./sites/default/...").
"""

from apps.offres.scrapers import mali as m

ENTETE = ("<tr><th>Nom Autorité Contractante</th><th>Nom service</th>"
          "<th>Libellé du Dossier</th><th>Date du dossier</th><th>Dossier</th></tr>")


def ligne(autorite, service, libelle, date_dossier, fichier=None):
    doc = (f'<a href="./sites/default/files/DATA_IN/{fichier}" title="Télécharger le document">Télécharger</a>'
           if fichier else "")
    return (f"<tr><td>{autorite}</td><td>{service}</td><td>{libelle}</td>"
            f'<td align="center">{date_dossier}</td><td align="center">{doc}</td></tr>')


def page(*lignes):
    return f'<table class="responstable DataTable">{ENTETE}{"".join(lignes)}</table>'


def test_decoupe_le_tableau_sans_l_entete():
    html = page(ligne("CMSS", "CMSS", "Climatiseurs", "28/07/2026", "235857_AAO_613988.docx"),
                ligne("CMSS", "CMSS", "Groupe electrogene", "28/07/2026", "235858_AAO_613895.docx"))
    assert len(m.lignes_du_tableau(html)) == 2


def test_identifiant_vient_du_numero_de_fichier():
    cellules = m.lignes_du_tableau(page(ligne("A", "S", "L", "28/07/2026", "235857_AAO_613988.docx")))[0]
    item = m.normalize(cellules, "Appel d'offres")
    assert item["id"] == "ml-235857", item["id"]
    assert item["lien"] == "https://www.dgmp.gouv.ml/sites/default/files/DATA_IN/235857_AAO_613988.docx"


def test_ligne_sans_dossier_est_hachee_et_stable():
    a = m.normalize(m.lignes_du_tableau(page(ligne("A", "S", "L", "28/07/2026")))[0], "AO")
    b = m.normalize(m.lignes_du_tableau(page(ligne("A", "S", "L", "28/07/2026")))[0], "AO")
    c = m.normalize(m.lignes_du_tableau(page(ligne("A", "S", "Autre", "28/07/2026")))[0], "AO")
    assert a["id"] == b["id"] and a["id"] != c["id"]
    assert a["lien"].startswith("https://www.dgmp.gouv.ml/"), "repli sur la page de la liste"


def test_normalisation():
    cellules = m.lignes_du_tableau(page(ligne("MINISTERE X", "PROJET Y", "Recrutement d'un consultant",
                                              "14/07/2026", "234752_AMI_635415.doc")))[0]
    item = m.normalize(cellules, "Manifestation d'interet")
    assert item["source"] == "mali" and item["pays"] == "Mali"
    assert item["organisation"] == "MINISTERE X"
    assert item["date_publication"] == "2026-07-14"
    assert item["date_limite"] == "", "le portail ne publie pas d'echeance"
    assert item["description"] == "Manifestation d'interet. Service PROJET Y. Recrutement d'un consultant"


def test_ligne_incomplete_est_ignoree():
    html = page("<tr><td>A</td><td>B</td><td>C</td></tr>")
    assert m.lignes_du_tableau(html) == []


def test_date():
    assert m.date_iso("28/07/2026") == "2026-07-28"
    assert m.date_iso("31/02/2026") == ""
    assert m.date_iso("") == ""


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
