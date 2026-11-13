"""Tests de la normalisation des avis PPIP (Kenya).

Sans reseau ni dependance : `python test_kenya.py`.
"""

from apps.offres.scrapers import kenya as k

AVIS = {
    "id": 304524, "title": "SUPPLY AND DELIVERY OF DESKTOP COMPUTERS", "tender_ref": "KNH/T/12/2026-2027",
    "published_at": "2026-08-31 00:00:00", "close_at": "2026-09-15 00:00:00", "tender_fee": 1000,
    "description": None, "is_reservation": 0,
    "pe": {"id": 5000, "name": "Kenyatta National Hospital"},
    "procurement_method": {"title": "Open Tender", "code": "open"},
    "procurement_category": {"title": "Goods", "code": "goods"},
}


def test_normalisation():
    item = k.normalize(AVIS)
    assert item["id"] == "ke-304524" and item["source"] == "kenya" and item["pays"] == "Kenya"
    assert item["titre"] == "SUPPLY AND DELIVERY OF DESKTOP COMPUTERS"
    assert item["organisation"] == "Kenyatta National Hospital"
    assert item["date_limite"] == "2026-09-15" and item["date_publication"] == "2026-08-31"
    assert item["description"] == ("Open Tender. Goods. Ref KNH/T/12/2026-2027. Tender fee 1000 KES. "
                                   "SUPPLY AND DELIVERY OF DESKTOP COMPUTERS"), item["description"]
    assert item["lien"] == "https://tenders.go.ke/tenders/304524"


def test_description_distincte_remplace_le_titre_dans_le_corps():
    item = k.normalize(dict(AVIS, description="200 units for the ICT department"))
    assert item["description"].endswith("200 units for the ICT department")


def test_exclusions():
    assert not k.est_exclu(AVIS)
    assert k.est_exclu(dict(AVIS, is_reservation=1)), "reserve AGPO"
    assert k.est_exclu(dict(AVIS, procurement_method={"title": "Restricted Tendering"}))
    assert k.est_exclu(dict(AVIS, procurement_method={"title": "Direct Procurement"}))
    assert not k.est_exclu(dict(AVIS, procurement_method={"title": "Expression of Interest"}))
    assert not k.est_exclu(dict(AVIS, procurement_method=None))


def test_dates():
    assert k.date_iso("2026-09-15 00:00:00") == "2026-09-15"
    assert k.date_iso(None) == ""


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
