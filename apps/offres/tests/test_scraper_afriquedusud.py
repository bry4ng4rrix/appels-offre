"""Tests de la normalisation des avis eTenders (Afrique du Sud).

Sans reseau ni dependance : `python test_afriquedusud.py`.
"""

from apps.offres.scrapers import afriquedusud as z

AVIS = {
    "id": 170198, "tender_No": "CTICC 012/2027",
    "description": "Appointment of an Internet Service Provider",
    "category": "Information service activities", "type": "Request for Bid(Open-Tender)",
    "organ_of_State": "Cape Town International Convention Centre",
    "closing_Date": "2026-10-16T12:00:00", "date_Published": "2026-09-14T00:00:00",
    "province": "Western Cape", "briefingCompulsory": True,
    "supportDocument": [
        {"supportDocumentID": "3ccce17c-1aea-42c1-8eb6-ae0340fcfa3e", "fileName": "CTICC 012 Advert.pdf",
         "extension": ".pdf", "active": True},
    ],
}


def test_normalisation():
    item = z.normalize(AVIS)
    assert item["id"] == "za-170198"
    assert item["source"] == "afriquedusud" and item["pays"] == "Afrique du Sud"
    assert item["titre"] == "Appointment of an Internet Service Provider"
    assert item["organisation"] == "Cape Town International Convention Centre"
    assert item["date_limite"] == "2026-10-16" and item["date_publication"] == "2026-09-14"
    assert item["description"] == ("Request for Bid(Open-Tender). Category Information service activities. "
                                   "Province Western Cape. Tender CTICC 012/2027. Compulsory briefing session. "
                                   "Appointment of an Internet Service Provider"), item["description"]


def test_lien_reproduit_la_construction_du_portail():
    lien = z.lien_du_document(AVIS)
    assert lien == ("https://www.etenders.gov.za/home/Download/"
                    "?blobName=3ccce17c-1aea-42c1-8eb6-ae0340fcfa3e.pdf"
                    "&downloadedFileName=CTICC%20012%20Advert.pdf"), lien


def test_sans_piece_jointe_le_lien_est_la_page():
    sans = dict(AVIS, supportDocument=[])
    assert z.normalize(sans)["lien"] == z.ZA_PAGE
    inactif = dict(AVIS, supportDocument=[dict(AVIS["supportDocument"][0], active=False)])
    assert z.normalize(inactif)["lien"] == z.ZA_PAGE


def test_valeurs_na_sont_ignorees():
    item = z.normalize(dict(AVIS, province="N/A", briefingCompulsory=False, category=None))
    assert "Province" not in item["description"] and "Category" not in item["description"]
    assert "briefing" not in item["description"]


def test_dates():
    assert z.date_iso("2026-10-16T12:00:00") == "2026-10-16"
    assert z.date_iso(None) == "" and z.date_iso("0001-01-01T00:00:00") == "0001-01-01"


def test_titre_de_repli():
    assert z.normalize(dict(AVIS, description=""))["titre"] == "CTICC 012/2027"


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
