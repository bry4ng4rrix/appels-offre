"""Tests du decoupage des "Open Bids" du CPBN (Namibie).

Sans reseau ni dependance : `python test_namibie.py`.

Deux pieges constates le 14/09/2026 :

  - le titre de la carte se termine par ": REFERENCE" ;
  - les dates s'ecrivent avec un suffixe ordinal, "14th October, 2026".
"""

from apps.offres.scrapers import namibie as n


def carte(numero, titre, reference, cloture):
    return f'''<tr><td><div class="card">
      <div class="card-body"><h4 class="card-title">
        <a href="https://www.cpbn.com.na/index/bid/{numero}">{titre}: {reference}</a></h4></div>
      <ul class="list-group"><li class="list-group-item"><strong>Reference number:</strong> {reference} |
        <strong>Closing Date and Time:</strong> {cloture} |
        <i><strong><a href="https://www.cpbn.com.na/index/bid/{numero}">More Details</a></strong></i></li></ul>
    </div></td></tr>'''


def page(*cartes):
    return f'<table id="activeBidsTable"><tr><th>Bid Title</th></tr>{"".join(cartes)}</table>'


FICHE = """<html><body><p>Bid Details</p><p>Category:</p><p>Goods</p>
<p>Institution:</p><p>Ministry of Health</p><p>Description of the Bid</p><p>Vehicles</p>
<p>Date of Issue</p><p>28th August, 2026</p><p>Closing Date and Time</p><p>5th October, 2026 11:00</p></body></html>"""


def test_dates_ordinales():
    assert n.date_iso("14th October, 2026 11:00") == "2026-10-14"
    assert n.date_iso("2nd October, 2026 11:00") == "2026-10-02"
    assert n.date_iso("1st January 2027") == "2027-01-01"
    assert n.date_iso("") == "" and n.date_iso("31st February, 2026") == ""


def test_decoupe_les_cartes():
    cartes = n.cartes_de_la_page(page(
        carte(113, "Provision of Security Services", "NCS/OAB/CPBN-04/2026", "14th October, 2026 11:00"),
        carte(114, "Supply of Petrol", "G/ONB/CPBN-10/2026", "13th October, 2026 11:00")))
    assert [c["numero"] for c in cartes] == ["113", "114"]
    assert cartes[0]["titre"] == "Provision of Security Services", cartes[0]["titre"]
    assert cartes[0]["reference"] == "NCS/OAB/CPBN-04/2026"
    assert cartes[0]["cloture"] == "14th October, 2026 11:00"
    assert n.cartes_de_la_page("<table id='x'></table>") == []


def test_fiche():
    ch = n.champs_de_la_fiche(FICHE)
    assert ch == {"Category": "Goods", "Institution": "Ministry of Health",
                  "Date of Issue": "28th August, 2026"}, ch


def test_normalisation():
    c = n.cartes_de_la_page(page(carte(116, "Supply of 68 vehicles", "G/ONB/CPBN-11/2026",
                                       "5th October, 2026 11:00")))[0]
    item = n.normalize(c, n.champs_de_la_fiche(FICHE))
    assert item["id"] == "na-116" and item["source"] == "namibie" and item["pays"] == "Namibie"
    assert item["organisation"] == "Ministry of Health"
    assert item["date_limite"] == "2026-10-05" and item["date_publication"] == "2026-08-28"
    assert item["description"] == "Goods. Reference G/ONB/CPBN-11/2026. Supply of 68 vehicles"
    assert item["lien"] == "https://www.cpbn.com.na/index/bid/116"


def test_sans_fiche_l_organisation_est_l_office():
    c = n.cartes_de_la_page(page(carte(1, "T", "R", "5th October, 2026")))[0]
    assert n.normalize(c, {})["organisation"] == "Central Procurement Board of Namibia"


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
