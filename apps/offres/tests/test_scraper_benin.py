"""Tests de la normalisation des dossiers de l'API SIGMAP (Benin).

Sans reseau ni dependance : `python test_benin.py`.
"""

from apps.offres.scrapers import benin as b

DOSSIER = {
    "dosID": 1226942,
    "appelsoffres": {"apoID": 1226921, "apoObjet": "Travaux de construction et équipement des centres",
                     "apoReference": "T_PRIMA_116616", "typemarche": {"code": "T", "libelle": "Travaux"}},
    "autoriteContractante": {"denomination": "Société des Infrastructures Routières (SIRAT)"},
    "dosDateCreation": "2026-09-03", "dosDatePublication": "2026-09-07",
    "dosDateLimiteDepot": "2026-10-23", "dosReference": "T_PRIMA_116616",
    "dosNombreLots": 2, "dosFichier": "https://bi.marches-publics.bj/x.pdf", "expired": False,
}


def test_normalisation():
    item = b.normalize(DOSSIER)
    assert item["id"] == "bj-1226942" and item["source"] == "benin" and item["pays"] == "Bénin"
    assert item["titre"] == "Travaux de construction et équipement des centres"
    assert item["organisation"] == "Société des Infrastructures Routières (SIRAT)"
    assert item["date_limite"] == "2026-10-23" and item["date_publication"] == "2026-09-07"
    assert item["description"] == ("Travaux. Reference T_PRIMA_116616. 2 lots. "
                                   "Travaux de construction et équipement des centres"), item["description"]
    assert item["lien"] == "https://marches-publics.bj/appels-doffres/1226942"


def test_publication_absente_replie_sur_la_creation():
    item = b.normalize(dict(DOSSIER, dosDatePublication=None))
    assert item["date_publication"] == "2026-09-03"


def test_un_seul_lot_n_est_pas_mentionne():
    assert "lot" not in b.normalize(dict(DOSSIER, dosNombreLots=1))["description"]


def test_champs_manquants():
    item = b.normalize({"dosID": 5, "appelsoffres": None, "autoriteContractante": None})
    assert item["titre"] == "Avis Benin" and item["organisation"] == "" and item["date_limite"] == ""


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
