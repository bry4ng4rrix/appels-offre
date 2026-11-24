"""Sixieme vague du 19/11/2026 : 30 sources (RSS, OCDS, Socrata, API, pages HTML). Sans reseau."""

from datetime import date, timedelta
from unittest.mock import patch

from apps.offres.scrapers import flux, nationaux, ocds, ong, organisations, portails
from apps.offres.tests.outils import en_cas_de_test

DEMAIN = (date.today() + timedelta(days=1)).isoformat()
HIER = (date.today() - timedelta(days=1)).isoformat()


def test_date_libre():
    d = organisations.date_libre
    assert d("receipt of offers: 23-November-2026, 4:30PM") == "2026-11-23"
    assert d("Monday 23rd November 2026 @ 17:00") == "2026-11-23"
    assert d("no later than Thursday, November 5, 2026 at 10:00") == "2026-11-05"
    assert d("Mon, 24 February 2025 5:00 pm") == "2025-02-24"
    assert d("sans date") == ""


# --- Flux RSS et OCDS ---

def _entree(**k):
    return {"titre": "Titre", "guid": "", "lien": "", "date": "2026-11-19", "resume": "", **k}


def test_rbi():
    lien = "https://www.rbi.org.in/scripts/BS_ViewTenders.aspx?id=26192"
    item = flux.RbiScraper().normalize(_entree(guid=lien, lien=lien))
    assert item["id"] == "rbi-26192" and item["pays"] == "Inde"


def test_allemagne_ignore_les_attributions():
    lien = "https://www.service.bund.de/IMPORTE/Ausschreibungen/editor/Kreis-Viersen/2026/11/6717912.html"
    appel = _entree(guid=lien, lien=lien + "#track=feed-callforbids", resume=(
        "Erf&uuml;llungsort: <strong>Wegberg</strong><br/>Vergabestelle: <strong>Kreis Viersen</strong>"
        "<br/>Angebotsfrist: <strong>10.12.2026 10:00</strong>"))
    item = flux.AllemagneScraper().normalize(appel)
    assert item["id"] == "de-6717912" and item["organisation"] == "Kreis Viersen"
    assert item["date_limite"] == "2026-12-10" and item["lien"] == lien
    attribution = dict(appel, resume="Vergabestelle: <strong>BImA, Berlin</strong><br/>Angebotsfrist: <br/>")
    assert flux.AllemagneScraper().normalize(attribution) is None


def test_find_a_tender():
    release = {"id": "109733-2026", "ocid": "ocds-h6vhtk-07bf83", "date": "2026-11-19T13:05:44Z",
               "buyer": {"name": "Perth & Kinross Council"},
               "tender": {"status": "active", "title": "Central Heating Upgrade",
                          "tenderPeriod": {"endDate": "2027-01-07T12:00:00Z"}}}
    item = ocds.FindATenderScraper().normalize(release)
    assert item["id"] == "fts-ocds-h6vhtk-07bf83" and item["date_limite"] == "2027-01-07"
    assert item["lien"] == "https://www.find-tender.service.gov.uk/Notice/109733-2026"
    assert ocds.FindATenderScraper().normalize(dict(release, tender={**release["tender"], "status": "complete"})) is None


# --- Socrata, CKAN, API ---

def test_los_angeles():
    item = portails.LosAngelesScraper().convertir({
        "rampid": "232738", "title": "HAND PUMP AND BLOWER", "type": "IFB", "department": "Water & Power",
        "bidpost": "2026-10-27T22:36:47.000", "closedate": "2026-11-19T22:00:00.000",
        "url": {"url": "https://www.rampla.org/s/opportunity-details?id=006"}})
    assert item["id"] == "la-232738" and item["date_limite"] == "2026-11-19"
    assert item["lien"] == "https://www.rampla.org/s/opportunity-details?id=006"


def test_delaware_et_montgomery():
    de = portails.DelawareScraper().convertir({
        "contractnumber": "BSD270003", "contracttitle": "Design Services", "opendate": "2026-11-10T00:00:00.000",
        "deadlinedate": "2026-12-03T00:00:00.000", "agencycode": "BSD", "bidurl": {"url": "https://mmp.delaware.gov/Bids/Details/9393"}})
    assert de["id"] == "de-BSD270003" and de["lien"] == "https://mmp.delaware.gov/Bids/Details/9393"
    mc = portails.MontgomeryScraper().convertir({
        "number": "1200740", "description": "Commissary Services", "type": "RFP",
        "issuancedate": "2026-10-20T00:00:00.000", "closingdate": "2026-11-20T00:00:00.000"})
    assert mc["id"] == "mcmd-1200740" and mc["lien"] == portails.MontgomeryScraper.site


def test_texas_dot_regroupe_par_projet():
    assert "$group" in portails.TexasDotScraper.extra
    item = portails.TexasDotScraper().convertir({
        "project_id": "A00062892", "county": "Ellis", "highway": "IH 45", "district_division": "Dallas",
        "project_classification": "Interchange", "proposal_published_date": "2026-11-06T10:01:42.000",
        "bid_recieved_until_date_and": "2026-12-01T13:00:00.000", "sealed_engineer_s_estimate": "116272606.72"})
    assert item["id"] == "txdot-A00062892" and item["titre"] == "Interchange - IH 45, comte de Ellis"
    assert "116,272,607 USD" in item["description"]


def test_erate():
    item = portails.ErateScraper().convertir({
        "application_number": "270004822", "billed_entity_name": "St Peter Catholic School",
        "billed_entity_city": "Marshall", "billed_entity_state": "MO", "funding_year": "2027",
        "certified_datetime": "2026-11-18T21:06:00.000", "allowable_contract_date": "2026-12-16T00:00:00.000",
        "category_one_description": "Internet service", "f470_number": {"url": "https://publicdata.usac.org/x"}})
    assert item["id"] == "erate-270004822" and item["titre"].endswith("(Marshall, MO)")
    assert item["date_limite"] == "2026-12-16"


def test_toronto_dedoublonne_et_ecarte_les_clos():
    ligne = {"Document Number": "5821214840", "RFx (Solicitation) Type": "RFP", "Issue Date": "2026-11-02",
             "Submission Deadline": DEMAIN, "Division": "Technology Services",
             "Solicitation Document Description": "Request for Proposals for Remediation. It is the intention..."}
    clos = dict(ligne, **{"Document Number": "1", "Submission Deadline": HIER})
    with patch.object(portails, "get_json", return_value={"result": {"records": [ligne, ligne, clos]}}):
        items = portails.TorontoScraper().scrape(set(), complet=True)
    assert [i["id"] for i in items] == ["to-5821214840"]
    assert items[0]["titre"] == "Request for Proposals for Remediation"


def test_pays_bas():
    page = {"content": [
        {"publicatieId": "449953", "publicatieDatum": date.today().isoformat(), "aanbestedingNaam": "WMO Trapliften",
         "opdrachtgeverNaam": "Gemeente Helmond", "sluitingsDatum": DEMAIN + "T12:00:00",
         "link": {"href": "https://www.tenderned.nl/aankondigingen/overzicht/449953"}},
        {"publicatieId": "2", "publicatieDatum": "2020-01-01", "aanbestedingNaam": "Ancien", "sluitingsDatum": HIER}]}
    with patch.object(portails, "get_json", return_value=page) as appel:
        items = portails.PaysBasScraper().scrape(set(), complet=True)
    assert [i["id"] for i in items] == ["nl-449953"] and items[0]["organisation"] == "Gemeente Helmond"
    assert appel.call_args.args[2]["publicatieType"] == "AAO"
    assert appel.call_count == 1, "page plus ancienne que la fenetre : on s'arrete"


def test_roumanie():
    avis = {"cNoticeId": 100213749, "noticeNo": "CN1097975", "contractTitle": "Dezinfectant",
            "contractingAuthorityNameAndFN": "5002142 - Spitalul Clinic Craiova",
            "noticeStateDate": "2026-11-03T13:00:40+02:00", "maxTenderReceiptDeadline": "2026-12-07T15:00:00+02:00"}
    with patch.object(portails, "post_json", return_value={"items": [avis]}) as appel:
        (item,) = portails.RoumanieScraper().scrape(set(), complet=True)
    assert item["id"] == "ro-100213749" and item["organisation"] == "Spitalul Clinic Craiova"
    assert item["date_limite"] == "2026-12-07"
    assert item["lien"] == "https://www.e-licitatie.ro/pub/notices/c-notice/v2/view/100213749"
    assert appel.call_args.args[2]["startTenderReceiptDeadline"].startswith(date.today().isoformat())


# --- Pages HTML : organisations et portails ---

def test_seae():
    html = """<div class="node--type-tender"><div class="field--name-field-category">Services</div>
     <h3 class="card-title"><a href="/delegations/tanzania/provision-travel-agency-services_en"> Travel agency </a></h3>
     <div class="deadline"><time datetime="2026-11-27T12:00:00Z">27.11.2026</time></div></div>"""
    (item,) = organisations.SeaeScraper().extraire(html)
    assert item["id"] == "seae-provision-travel-agency-services" and item["pays"] == "Tanzania"
    assert item["date_limite"] == "2026-11-27"


def test_bce_ignore_les_attributions():
    html = """<div class="definition-list -filter"><dl>
     <dt isodate="2026-10-30"></dt><dd><div class="category">PROCUREMENT CONTRACT NOTICE</div>
      <div class="title"><a href="/ecb/proc/x.pdf?abc">Contract Notice: ECB - Legal translation (750606-2026)</a></div>
      <div class="content-box"><dl><dt>Closing date</dt><dd>2026-11-27</dd></dl></div></dd>
     <dt isodate="2026-10-30"></dt><dd><div class="category">PROCUREMENT CONTRACT AWARD NOTICE</div>
      <div class="title"><a href="/ecb/proc/y.pdf">Contract Award Notice</a></div></dd></dl></div>"""
    (item,) = organisations.BceScraper().extraire(html)
    assert item["id"] == "bce-750606-2026" and item["date_limite"] == "2026-11-27"


def test_victoria_ecarte_les_exercices():
    ligne = """<tr data-tender-code="{code}"><td class="tender-code-state">{code} Open</td>
     <td><a class="tenderRowTitle" href="/tender/view?id=285775">{titre}</a>
     <span class="line-item-detail">Issued by: Transport Accident Commission</span></td>
     <td><span class="opening_date">Mon, 24 February 2025 5:00 pm</span>
     <span class="closing_date">Mon, 25 February 2030 5:00 pm</span></td></tr>"""
    html = "<table>" + ligne.format(code="PROCF23-149", titre="Clinical Advisory") \
        + ligne.format(code="DEMO", titre="Tenders ACT Practice ATM") + "</table>"
    (item,) = nationaux.VictoriaScraper().extraire(html)
    assert item["id"] == "vic-PROCF23-149" and item["organisation"] == "Transport Accident Commission"
    assert item["date_publication"] == "2025-02-24" and item["date_limite"] == "2030-02-25"
    assert item["lien"] == "https://www.tenders.vic.gov.au/tender/view?id=285775"


def test_australie_occidentale():
    html = """<table><tbody><tr><td class="left top"><b>RFIHSS202616730</b></td>
     <td><a href="/watenders/tender/display/tender-details.action?id=71251&amp;returnUrl=%2Fx">Procurement System</a>
     <span class="SUMMARY_SMALL">Issued by Health Support Services UNSPSC: software</span></td>
     <td><span class="SUMMARY_CLOSINGDATE"> 10 Feb, 2027 2:30 PM </span></td></tr></tbody></table>"""
    (item,) = nationaux.AustralieOccidentaleScraper().extraire(html)
    assert item["id"] == "wa-71251" and item["date_limite"] == "2027-02-10"
    assert item["organisation"] == "Health Support Services"
    assert item["lien"] == "https://www.tenders.wa.gov.au/watenders/tender/display/tender-details.action?id=71251"


def test_eswatini():
    html = """<div class="list-item job-box"><h5>5 year Lease of a colour printer</h5>
     <p><b>Micro Projects</b></p><p> MPCU-EYP-TEN-001 </p><p><b>Tender Type:</b> Open Tender</p>
     <p> Submission Deadline: Friday 20th November 2026 10:00 am</p>
     <a href="documents/tenders/Micro%20Projects/t.pdf">Download Tender</a></div>"""
    (item,) = nationaux.EswatiniScraper().extraire(html)
    assert item["id"] == "sz-MPCU-EYP-TEN-001" and item["organisation"] == "Micro Projects"
    assert item["date_limite"] == "2026-11-20"
    assert item["lien"] == "https://www.esppra.co.sz/documents/tenders/Micro%20Projects/t.pdf"


def test_congo():
    html = """<table><tr class="marche-row-accueil"><td><strong> AON N°001/MASAH/CGMP/2026 </strong></td>
     <td><div class="marche-title-accueil"> Acquisition des kits </div></td>
     <td><span class="text-muted"> Ministère des Affaires sociales... </span></td>
     <td><div class="date-text"> 03/12/2026 </div></td></tr></table>"""
    (item,) = nationaux.CongoScraper().extraire(html)
    assert item["id"] == "cg-AON N°001/MASAH/CGMP/2026" and item["date_limite"] == "2026-12-03"
    assert item["organisation"] == "Ministère des Affaires sociales"


def test_haiti_prend_le_titre_complet():
    html = """<article class="appels-grid-card"><span class="appels-date-badge"> 22/10/2026 </span>
     <img alt="Avis d'Appel d'Offres Ouvert National pour l'Acquisition de Produits Alimentaires"/>
     <h2 class="appels-card-title"> Avis d'Appel d'Offres Ouvert... </h2>
     <div class="appels-authority"><span>Police Nationale d’Haïti</span></div>
     <a href="https://www.cnmp.gouv.ht/uploads/documents/177_AAO.pdf">Télécharger</a></article>"""
    (item,) = nationaux.HaitiScraper().extraire(html)
    assert item["titre"].endswith("Produits Alimentaires") and item["id"] == "ht-177_AAO.pdf"
    assert item["date_publication"] == "2026-10-22" and item["organisation"] == "Police Nationale d’Haïti"


def test_mozambique():
    html = """<label class="label_roll"><br>CONCURSO LIMITADO: 14/ISCAM/UGEA/2026<br>
     <label class=lbl_objecto>LIMPEZA E HIGIENIZACAO</label><br>INSTITUTO SUPERIOR DE CONTABILIDADE<br>
     VALIDADE: <u>2026-11-24</u><br><a href='concurso_detalhes.php?referencia=14/ISCAM/UGEA/2026'>VER</a></label>"""
    (item,) = nationaux.MozambiqueScraper().extraire(html)
    assert item["id"] == "mz-14/ISCAM/UGEA/2026" and item["organisation"] == "INSTITUTO SUPERIOR DE CONTABILIDADE"
    assert item["date_limite"] == "2026-11-24" and item["description"].startswith("CONCURSO LIMITADO")


# --- Pages HTML : ONG ---

def test_nrc():
    html = """<a href="/tender/prequalification-works" class="x"><h2>Prequalification of Works</h2><time>08. Nov 2026</time></a>"""
    (item,) = ong.NrcScraper().extraire(html)
    assert item["id"] == "nrc-prequalification-works" and item["date_publication"] == "2026-11-08"


def test_drc_ignore_les_archives():
    art = """<article class="tenderList__item" data-country="east africa | kenya" data-published="20261110"
     data-deadline="20261120" data-status="{statut}"><span class="tenderList__item__title">{titre}</span>
     <a class="casper" href="/en/tenders/{titre}/"></a></article>"""
    html = art.format(statut="current", titre="research") + art.format(statut="archived", titre="vieux")
    (item,) = ong.DrcScraper().extraire(html)
    assert item["id"] == "drc-research" and item["pays"] == "Kenya"
    assert item["date_publication"] == "2026-11-10" and item["date_limite"] == "2026-11-20"


def test_goal():
    html = """<span class="fl-heading-text">GOAL Ethiopia</span><div class="fl-accordion-item">
     <a class="fl-accordion-button-label">Cash Distribution Program</a><div class="fl-accordion-content">
     Reference: ADD-ZZ1-55587 Proposed Timelines: RFO Publication: 08-November-2026
     Closing date for clarifications: 20-November-2026 Closing date for receipt of offers: 23-November-2026, 4:30PM</div></div>"""
    (item,) = ong.GoalScraper().extraire(html)
    assert item["id"] == "goal-ADD-ZZ1-55587" and item["organisation"] == "GOAL Ethiopia"
    assert item["date_publication"] == "2026-11-08" and item["date_limite"] == "2026-11-23"


def test_plan_international():
    html = """<h3 class="wp-block-heading"><strong>ITT FY27-0228 Independent Consultant Review</strong></h3>
     <p>Plan International Mali is inviting interested parties to submit proposals.</p>
     <p>Responses should be submitted no later than <strong>Wednesday, November 25, 2026 at 10:00 AM</strong>.</p>
     <h3 class="wp-block-heading"></h3>"""
    (item,) = ong.PlanInternationalScraper().extraire(html)
    assert item["date_limite"] == "2026-11-25" and item["pays"] == "Mali"
    assert item["id"].startswith("plan-")


def test_islamic_relief_ne_garde_que_les_ouverts():
    ligne = """<div class="tenders"><div><span> 17 Nov</span></div><div><a href="https://islamic-relief.org/tenders/{s}/">
     <p>{s}</p></a></div><div><span> {etat} </span></div><div>Global</div><div></div></div>"""
    html = ligne.format(s="trainers", etat="Open") + ligne.format(s="ancien", etat="Closed")
    (item,) = ong.IslamicReliefScraper().extraire(html)
    assert item["id"] == "ir-trainers" and item["date_publication"].endswith("-11-17")
    assert item["date_publication"] <= date.today().isoformat()


def test_welthungerhilfe():
    html = """<div class="tender__list__item"><div class="tender__list__item__date">Date of Publication: &shy;19.11.2026</div>
     <div class="tender__list__item__title"><a href="https://eu.eu-supply.com/app/rfq/x.asp?PID=463364&amp;B=WHH">Kitchen Kits</a></div>
     <div class="tender__list__item__client">Contracting Authority: Welthungerhilfe Lebanon</div>
     <div class="tender__list__item__deadline">Response Deadline (CET): &shy;03.12.2026 10:12</div></div>"""
    (item,) = ong.WelthungerhilfeScraper().extraire(html)
    assert item["id"] == "whh-463364" and item["pays"] == "Lebanon"
    assert item["date_publication"] == "2026-11-19" and item["date_limite"] == "2026-12-03"


def test_hi_lit_le_sommaire():
    html = """<ul><li><p><a href="/fr/appels-d-offres#261110">Consultance internationale au Tchad</a></p></li>
     <li><p><a href="/fr/appels-d-offres#261030-1">Assurance groupe HI Bangladesh</a></p></li></ul>"""
    items = ong.HandicapInternationalScraper().extraire(html)
    assert [i["id"] for i in items] == ["hi-261110", "hi-261030-1"]
    assert items[0]["date_publication"] == "2026-11-10"


def test_irc_medair_sfa():
    irc = """<div class="rplc-teaser-basic"><a href=" /rfp/irc-uk-offline-media "><h2 class="rplc-teaser-basic__title"> Offline Media </h2>
     <div class="rplc-teaser-basic__date"><div>November 11, 2026</div></div></a></div>"""
    (i,) = ong.IrcScraper().extraire(irc)
    assert i["id"] == "irc-irc-uk-offline-media" and i["date_publication"] == "2026-11-11"
    medair = """<div class="card_tender_wrap"><h3 fs-cmsfilter-field="name">Medical Stock</h3>
     <p fs-cmsfilter-field="ref">Ref:</p><p fs-cmsfilter-field="ref">ITB-2026-0002290</p>
     <p fs-cmsfilter-field="country">Switzerland</p><p fs-cmsfilter-field="deadline">October 23, 2026</p>
     <a class="button" href="/tenders/medical-stock">View</a></div>"""
    (m,) = ong.MedairScraper().extraire(medair)
    assert m["id"] == "medair-ITB-2026-0002290" and m["date_limite"] == "2026-10-23" and m["pays"] == "Switzerland"
    sfa = """<div><a class="clickable-title" href="/tender/rfp-strategy "><h5>RFP Strategy</h5></a>
     <p>Deadline: <time datetime="2026-12-18T12:00:00Z">Friday</time></p></div>"""
    (s,) = ong.ScienceForAfricaScraper().extraire(sfa)
    assert s["id"] == "sfa-rfp-strategy" and s["date_limite"] == "2026-12-18"


Essais = en_cas_de_test(globals())
