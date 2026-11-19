"""Cinquieme vague du 19/11/2026 : WordPress, AIIB, pages HTML, Quebec, Suisse, New York. Sans reseau."""

from datetime import date, timedelta
from unittest.mock import patch

from apps.offres.scrapers import flux, ocds, organisations, portails, wordpress
from apps.offres.tests.outils import en_cas_de_test

DEMAIN = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
HIER = (date.today() - timedelta(days=1)).strftime("%Y%m%d")


def _csud(ident, fin):
    return {"id": ident, "date": date.today().isoformat() + "T12:12:28",
            "link": f"https://www.coordinationsud.org/appel-offre/{ident}/",
            "title": {"rendered": "Appel d&rsquo;offres&nbsp;: Mission de diagnostic"},
            "acf": {"date-fin": fin}}


def test_coordination_sud_echeance_et_clos():
    scraper = wordpress.CoordinationSudScraper()
    item = scraper.normalize(_csud(1, "20261209"))
    assert item["id"] == "csud-1" and item["date_limite"] == "2026-12-09"
    with patch.object(wordpress, "get_json", return_value=[_csud(2, DEMAIN), _csud(3, HIER)]) as appel:
        items = scraper.scrape(set(), complet=True)
    assert [i["id"] for i in items] == ["csud-2"], "un appel dont la date de fin est passee est clos"
    assert "acf" in appel.call_args.args[2]["_fields"]


def test_date_flux_aiib():
    assert flux.date_flux("Nov 19, 2026") == "2026-11-19"
    assert flux.date_flux("2026-11-04T13:59:33+0800") == "2026-11-04"


AIIB_RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Construction of Dual Gauge Railway Line</title>
 <link>https://www.aiib.org/en/opportunities/business/project-procurement/_download/Bangladesh/REOI.pdf</link>
 <pubDate>Nov 17, 2026</pubDate><description></description></item>
<item><title>Bukhara Region Water Supply</title>
 <link>https://www.aiib.org/en/projects/details/2026/_download/Uzbekistan/BWSP-S_RFB_03_Contract_AwardGoods.pdf</link>
 <pubDate>Nov 11, 2026</pubDate><description></description></item>
<item><title>Obigarm-Nurobod Road Project</title>
 <link>https://www.aiib.org/en/projects/details/2026/_download/Tajikistan/PP-for-S000671.xlsx</link>
 <pubDate>Nov 19, 2026</pubDate><description></description></item>
</channel></rss>"""


def test_aiib_projets_ne_garde_que_les_avis():
    items = [i for i in map(flux.AiibProjetsScraper().normalize, flux.entrees(AIIB_RSS)[0]) if i]
    assert len(items) == 1, "attributions et plans de passation (.xlsx) ecartes"
    assert items[0]["pays"] == "Bangladesh" and items[0]["date_publication"] == "2026-11-17"
    assert items[0]["id"] == "aiibp-en/opportunities/business/project-procurement/_download/Bangladesh/REOI.pdf"


def test_aiib_identifiant_ariba():
    entree = {"titre": "RFP for SAP", "guid": "https://x/#/RfxEvent/preview/1110030514?anId=ANONYMOUS",
              "lien": "https://x/#/RfxEvent/preview/1110030514?anId=ANONYMOUS",
              "date": "2026-11-04", "resume": "<p>RFP</p>"}
    assert flux.AiibScraper().normalize(entree)["id"] == "aiib-1110030514"


UA_HTML = """<table><tbody><tr>
 <td class="views-field-field-date"><time datetime="2026-11-19T07:38:49Z">2026-11-19</time> -
  <time datetime="2026-12-03T12:00:00Z">2026-12-03</time></td>
 <td class="views-field-title"><a href="/en/bids/20261119/consultancy-free-movement">Consultancy Service</a></td>
 <td class="views-field-field-tags-documents">Procurement/ Bids</td>
 <td class="views-field-field-text-bidnumber">ET-AUC-569896-CS-QCBS</td></tr></tbody></table>"""


def test_union_africaine():
    (item,) = organisations.UnionAfricaineScraper().extraire(UA_HTML)
    assert item["id"] == "ua-20261119/consultancy-free-movement"
    assert item["date_publication"] == "2026-11-19" and item["date_limite"] == "2026-12-03"
    assert item["description"].startswith("Ref ET-AUC-569896-CS-QCBS")
    assert item["lien"] == "https://au.int/en/bids/20261119/consultancy-free-movement"


RAVINALA_HTML = """<div class="offer-card"><h3 class="offer-card__upper-title"> AAO-RAV-26-041 </h3>
 <div class="offer-card__date"> Date limite : 04/12/2026 </div>
 <h4 class="offer-card__title"> CHALLENGE SOLUTIONS INNOVANTES </h4>
 <p class="offer-card__descr">Lot A</p>
 <a href="https://www.ravinala-airports.aero/marches-en-cours/aao-rav-26-041/" class="offer-card__download">Télécharger</a></div>"""


def test_ravinala():
    (item,) = organisations.RavinalaScraper().extraire(RAVINALA_HTML)
    assert item["id"] == "ravinala-AAO-RAV-26-041" and item["date_limite"] == "2026-12-04"
    assert item["pays"] == "Madagascar" and item["titre"] == "CHALLENGE SOLUTIONS INNOVANTES"


UNITAID_HTML = """<div class="open-proposal-list"><div class="row cfp-row">
 <div class="proposal-title"><h4>Integrated TB and Hepatitis C Care in&hellip;</h4></div>
 <div class="proposal-description"><p>Area for Intervention</p></div>
 <div class="item-link"><a href="https://unitaid.org/call-for-proposal/?sf_id=119Vj000003n2JuIAI">Learn more</a></div>
 <div class="proposal-date"><h5>Deadline</h5><p>Monday, 01 March 2027 at 12:00 CET</p></div></div></div>
<h3>Previous funding opportunities</h3><div class="open-proposal-list"><div class="row cfp-row">
 <div class="proposal-title"><h4>Ancien appel</h4></div>
 <div class="item-link"><a href="https://unitaid.org/call-for-proposal/?sf_id=ANCIEN">Learn more</a></div></div></div>"""


def test_unitaid_ne_lit_que_les_appels_ouverts():
    (item,) = organisations.UnitaidScraper().extraire(UNITAID_HTML)
    assert item["id"] == "unitaid-119Vj000003n2JuIAI" and item["date_limite"] == "2027-03-01"
    assert item["titre"] == "Integrated TB and Hepatitis C Care in"


PAKISTAN_HTML = """<table><tbody><tr class="cb-rt-main">
 <td data-label="Tender No"><strong class="cb-rt-name"> TS0000018504E </strong></td>
 <td data-label="Tender Details"><span><strong> PROCUREMENT OF VHF RADIO EQUIPMENT </strong>
  <small>for detail please visit https://www.pnsc.com.pk/tenders</small></span></td>
 <td data-label="Advertised"> Nov 19, 2026 </td>
 <td data-label="Closing"><strong> Dec 22, 2026 </strong><small>11:00 AM</small></td>
 <td data-label="Actions"><a href="/public/tenders/tender-details/TS0000018504E">voir</a></td></tr>
<tr class="cb-rt-detail"><td><span class="cb-rt-dv"><strong> Pakistan National Shipping Corporation </strong></span></td></tr>
</tbody></table>"""


def test_pakistan():
    (item,) = organisations.PakistanScraper().extraire(PAKISTAN_HTML)
    assert item["id"] == "pk-TS0000018504E" and item["organisation"] == "Pakistan National Shipping Corporation"
    assert item["date_publication"] == "2026-11-19" and item["date_limite"] == "2026-12-22"
    assert item["lien"] == "https://epms.ppra.gov.pk/public/tenders/tender-details/TS0000018504E"


SL_HTML = """<table><tr><th>Bidding Organization</th><th>Date Posted</th></tr>
<tr><td>MINISTRY OF FINANCE (MoF)</td><td>02-11-2026</td><td>01-12-2026</td><td>PROCUREMENT OF GOODS</td>
 <td><a href="https://nppa.gov.sl/wp-content/uploads/2026/11/EOI-SUNDRY.pdf">View</a></td></tr></table>"""


def test_sierra_leone():
    (item,) = organisations.SierraLeoneScraper().extraire(SL_HTML)
    assert item["id"] == "sl-EOI-SUNDRY.pdf" and item["organisation"] == "MINISTRY OF FINANCE (MoF)"
    assert item["date_publication"] == "2026-11-02" and item["date_limite"] == "2026-12-01"


def test_quebec_lit_le_dernier_export_hebdomadaire():
    ckan = {"result": {"resources": [
        {"name": "hebdo_20261102_20261108.json", "url": "https://x/ancien.json"},
        {"name": "hebdo_20261109_20261115.json", "url": "https://x/recent.json"},
        {"name": "mensuel_20261001_20261031.json", "url": "https://x/mois.json"}]}}
    release = {"ocid": "ocds-ec9k95-1", "tag": ["tender"], "date": "2026-11-13T11:16:19-05:00",
               "buyer": {"name": "Centre d'acquisitions gouvernementales"},
               "tender": {"title": "VIANDES DIVERSES", "tenderPeriod": {"endDate": "2026-12-18T14:00:00-05:00"},
                          "documents": [{"url": "https://seao.gouv.qc.ca/avis?ItemId=e7a0"}]}}
    export = {"releases": [release, dict(release, ocid="ocds-ec9k95-2", tag=["tenderUpdate"])]}
    with patch.object(ocds, "get_json", side_effect=[ckan, export]) as appel:
        lues, suite = ocds.QuebecScraper().releases(1, "")
    assert appel.call_args.args[0] == "https://x/recent.json" and suite == ""
    assert [r["ocid"] for r in lues] == ["ocds-ec9k95-1"], "un modificatif n'est pas un nouvel avis"
    item = ocds.QuebecScraper().normalize(lues[0])
    assert item["id"] == "qc-ocds-ec9k95-1" and item["date_limite"] == "2026-12-18"
    assert item["lien"] == "https://seao.gouv.qc.ca/avis?ItemId=e7a0" and item["pays"] == "Canada"


def test_suisse_prefere_le_francais():
    item = portails.normalize_simap({
        "id": "a858", "projectNumber": "33992", "projectSubType": "construction", "processType": "open",
        "publicationDate": "2026-11-19", "title": {"de": "Ersatzneubau", "fr": "Reconstruction", "en": None},
        "procOfficeName": {"de": "Gemeinde Vorderthal ", "fr": None},
        "orderAddress": {"cantonId": "SZ", "city": {"de": "Vorderthal"}}})
    assert item["titre"] == "Reconstruction" and item["organisation"] == "Gemeinde Vorderthal"
    assert item["lien"] == "https://www.simap.ch/fr/project-detail/a858"
    assert "Vorderthal (SZ)" in item["description"]


def test_suisse_suit_le_curseur():
    projet = {"id": "p1", "title": {"fr": "Travaux"}, "publicationDate": "2026-11-19"}
    pages = [{"projects": [projet], "pagination": {"lastItem": "20261119|1"}},
             {"projects": [dict(projet, id="p2")], "pagination": {"lastItem": "20261119|1"}}]
    with patch.object(portails, "get_json", side_effect=pages) as appel, patch.object(portails.time, "sleep"):
        items = portails.SuisseScraper().scrape(set(), complet=True)
    assert [i["id"] for i in items] == ["ch-p1", "ch-p2"]
    assert appel.call_args.args[2]["lastItem"] == "20261119|1"
    assert appel.call_count == 2, "curseur inchange : derniere page"


def test_new_york():
    item = portails.normalize_nyc({
        "request_id": "20260923005", "start_date": "2026-10-13T00:00:00.000", "agency_name": "Housing Authority",
        "short_title": "PLUMBING SERVICES", "selection_method_description": "Competitive Sealed Bids",
        "due_date": "2026-12-19T10:00:00.000", "additional_description_1": "<p>Scope of Work: Plumbing</p>"})
    assert item["id"] == "nyc-20260923005" and item["date_limite"] == "2026-12-19"
    assert item["organisation"] == "Ville de New York, Housing Authority"
    assert item["lien"] == "https://a856-cityrecord.nyc.gov/RequestDetail/20260923005"
    assert "Scope of Work: Plumbing" in item["description"]


Essais = en_cas_de_test(globals())
