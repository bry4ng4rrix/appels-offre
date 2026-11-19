"""Sources ajoutees le 19/11/2026 (UE, Grants.gov, Ouganda, Cote d'Ivoire, Enabel,
LuxDev, BERD, Rwanda, Canada, Nouvelle-Zelande). Sans reseau."""

from apps.offres.scrapers import (berd, canada, cote_ivoire, enabel, grants_gov, luxdev,
                                  nouvelle_zelande, ouganda, rwanda, ue_ft, wordpress)
from apps.offres.tests.outils import en_cas_de_test


def _ue(famille, ident, **meta):
    meta = {"type": [famille], "identifier": [ident], "title": ["Titre"],
            "startDate": ["2026-11-18T00:00:00.000+0000"], **meta}
    return {"url": "https://ec.europa.eu/x", "metadata": meta}


def test_ue_ft():
    marche = ue_ft.normalize(_ue("0", "abc-CN", callIdentifier=["ECDC/2026/OP/0030"],
                                 cftLeadContractingAuthorityCode=['[{"name":"ECDC"}]'],
                                 deadlineDate=["2026-12-21T16:00:59.000+0000"],
                                 description=["<p>Cadre &amp; services</p>"]), "2026-11-19")
    assert marche["id"] == "euft-abc-CN" and marche["organisation"] == "ECDC"
    assert marche["date_limite"] == "2026-12-21" and marche["date_publication"] == "2026-11-18"
    assert marche["description"] == "Marche de l'UE. Ref ECDC/2026/OP/0030. Cadre & services"

    vagues = ue_ft.normalize(_ue("1", "HORIZON-X", callTitle=["Cluster 1"], deadlineDate=[
        "2026-09-02T00:00:00.000+0000", "2027-01-03T00:00:00.000+0000"]), "2026-11-19")
    assert vagues["date_limite"] == "2027-01-03", "prochaine vague, pas la premiere echue"
    assert vagues["titre"] == "Cluster 1 - Titre" and vagues["organisation"] == "Commission europeenne"

    aide = ue_ft.normalize(_ue("2", "EuropeAid/188000/DD/ACT/MG",
                               closingDate=["2026-12-08T11:00:00Z"]), "2026-11-19")
    assert aide["pays"] == "Madagascar" and aide["date_limite"] == "2026-12-08", "repli sur closingDate"
    assert aide["organisation"] == "Commission europeenne (EuropeAid)"
    assert ue_ft.normalize(_ue("0", ""), "2026-11-19") is None


def test_grants_gov():
    item = grants_gov.normalize({"id": "356893", "number": "PAR-25-144", "title": " Recherche ",
                                 "agency": "NIH", "openDate": "10/29/2024", "closeDate": ""})
    assert item["id"] == "grantsgov-356893" and item["titre"] == "Recherche"
    assert item["date_publication"] == "2024-10-29" and item["date_limite"] == ""
    assert item["lien"] == "https://www.grants.gov/search-results-detail/356893"
    assert grants_gov.normalize({"id": "1"}) is None


UG_HTML = """<table><tbody><tr>
 <td><div><a href="https://egpuganda.go.ug/index/1_egp"><img></a></div>
  <div><a href="https://egpuganda.go.ug/index/1_egp" class="text-default font-weight-semibold">MOWT/WRKS/00005
   <div class="text-muted font-size-sm"><span></span> Ministry of Works</div></a></div></td>
 <td><span>Works</span></td><td><span>Low Cost Road...</span></td>
 <td><span>2026-11-13</span></td><td><span>2026-12-09</span></td><td></td>
</tr><tr><td colspan="6">Aucun avis</td></tr></tbody></table>"""


def test_ouganda():
    (item,) = ouganda.extraire(UG_HTML)
    assert item["id"] == "ug-1_egp" and item["organisation"] == "Ministry of Works"
    assert item["date_limite"] == "2026-12-09" and item["date_publication"] == "2026-11-13"
    assert item["description"] == "Works. Ref MOWT/WRKS/00005. Low Cost Road..."
    assert item["lien"] == "https://egpuganda.go.ug/index/1_egp"


CI_HTML = """<table><tbody><tr>
 <td>AOO26100131084</td><td>Travaux</td><td>Construction
 et rehabilitation</td><td>DISTRICT D'ABIDJAN</td>
 <td data-order="2026-10-29">29-10-2026</td><td data-order="2026-12-04">04-12-2026</td>
</tr><tr><td></td><td>Travaux</td><td></td><td></td><td></td><td></td></tr></tbody></table>"""


def test_cote_ivoire():
    (item,) = cote_ivoire.extraire(CI_HTML)
    assert item["id"] == "ci-AOO26100131084" and item["titre"] == "Construction et rehabilitation"
    assert item["date_limite"] == "2026-12-04" and item["date_publication"] == "2026-10-29"
    assert item["organisation"] == "DISTRICT D'ABIDJAN" and item["pays"] == "Côte d'Ivoire"


# --- Deuxieme vague : Enabel, LuxDev, BERD, Rwanda, Canada, Nouvelle-Zelande ---

ENABEL_FICHE = """<p><strong>Pays : </strong> RD Congo</p>
<p class=""><strong>Date de clôture : </strong> 15 December 2026 10:00 </p>
<div><p><strong>Status :</strong> Ouvert</p></div>"""


def test_enabel():
    article = {"id": 7, "date": "2026-11-18T11:45:57", "link": "https://www.enabel.be/fr/tenders/x/",
               "title": {"rendered": "March&eacute; de travaux"}}
    champs = enabel.champs_fiche(ENABEL_FICHE)
    item = enabel.normalize(article, champs)
    assert item["id"] == "enabel-7" and item["titre"] == "Marché de travaux"
    assert item["pays"] == "RD Congo" and item["date_limite"] == "2026-12-15"
    assert item["date_publication"] == "2026-11-18"
    assert enabel.normalize(article, dict(champs, status="Clôturé")) is None
    addendum = dict(article, title={"rendered": "Addendum n°001 lignes directives"})
    assert enabel.normalize(addendum, champs) is None, "un addendum n'est pas un nouvel appel"


LUX_HTML = """<li class="views-row"><a href="/en/tenders/call-tenders/renovation">
 <header><span>Open</span><span></span><span>Laos</span></header>
 <h3>Renovation works</h3>
 <footer><span>A-LAO037-2026-0386</span><span></span><span>Works</span><span></span>
 <span>Deadline: 16.12.2026</span></footer></a></li>"""


def test_luxdev():
    (item,) = luxdev.extraire(LUX_HTML)
    assert item["id"] == "luxdev-A-LAO037-2026-0386" and item["pays"] == "Laos"
    assert item["statut"] == "Open" and item["date_limite"] == "2026-12-16"
    assert item["description"] == "Works. Ref A-LAO037-2026-0386. Renovation works"
    assert item["lien"] == "https://luxdev.lu/en/tenders/call-tenders/renovation"


def _berd(nid, etat):
    return f"""<tr><td><a href="viewNotice.html?displayNoticeId={nid}">Uzbekistan: Rehabilitation of WWTP</a></td>
     <td>Invitation For Tenders Single</td><td>NWP-13.2</td><td>13/11/2026 06:00 UK Time</td>
     <td>29/12/2026 10:00 UK Time</td><td>{etat}</td><td>x</td><td>[Namangan Water]</td></tr>"""


def test_berd():
    (item,) = berd.extraire("<table>" + _berd(1, "Open") + _berd(2, "Closed") + "</table>")
    assert item["id"] == "ebrd-1" and item["pays"] == "Uzbekistan"
    assert item["titre"] == "Rehabilitation of WWTP"
    assert item["date_limite"] == "2026-12-29" and item["date_publication"] == "2026-11-13"
    assert item["description"] == "Invitation For Tenders Single. Projet Namangan Water. NWP-13.2"


def _rw(ref, statut):
    return f"""<tr><td><input type="checkbox"></td><td>Supply of IT Equipment</td><td>{ref}</td>
     <td>{statut}</td><td>16/11/2026</td><td>16/12/2026 10:00</td><td>16/12/2026 10:30</td><td>one stage</td></tr>"""


def test_rwanda():
    html = "<table>" + _rw("000004/G/NCB/2026/2027/RCAA", "Published") \
        + _rw("000005/W/NCB/2026/2027/RCAA", "Cancelled") + "</table>"
    (item,) = rwanda.extraire(html)
    assert item["id"] == "rw-000004/G/NCB/2026/2027/RCAA" and item["organisation"] == "RCAA"
    assert item["date_limite"] == "2026-12-16" and item["date_publication"] == "2026-11-16"
    assert item["description"].startswith("Goods. NCB. Ref 000004/G/NCB/2026/2027/RCAA.")


CA_CSV = '''"title-titre-eng","title-titre-fra","referenceNumber-numeroReference","publicationDate-datePublication","tenderClosingDate-appelOffresDateCloture","procurementMethod-methodeApprovisionnement-fra","regionsOfDelivery-regionsLivraison-fra","contractingEntityName-nomEntitContractante-fra","noticeURL-URLavis-fra","tenderDescription-descriptionAppelOffres-fra"
"Repairs","Réparations","MX-1","2026-11-05","2026-12-15T14:00:00","Concurrentielle","*Québec","VIA Rail","https://www.merx.com/1?language=FR","La flotte a d&eacute;pass&eacute;"
"","","","","","","","","",""
'''


def test_canada():
    (item,) = canada.extraire(CA_CSV)
    assert item["id"] == "ca-MX-1" and item["titre"] == "Réparations"
    assert item["date_limite"] == "2026-12-15" and item["organisation"] == "VIA Rail"
    assert item["description"] == "Concurrentielle. Livraison : Québec. La flotte a dépassé"


NZ_RSS = b"""<?xml version="1.0"?><rss><channel><item>
 <title>Online job advertising</title>
 <link>https://www.gets.govt.nz//MSD/ExternalTenderDetails.htm?id=32705858</link>
 <description>&lt;table&gt;&lt;tr&gt;&lt;td&gt;&lt;b&gt;RFx ID: &lt;/b&gt;&lt;/td&gt;&lt;td&gt;32705858&lt;/td&gt;&lt;/tr&gt;
 &lt;tr&gt;&lt;td&gt;&lt;b&gt;Organisation: &lt;/b&gt;&lt;/td&gt;&lt;td&gt;MSD&lt;/td&gt;&lt;/tr&gt;
 &lt;tr&gt;&lt;td&gt;&lt;b&gt;Open date: &lt;/b&gt;&lt;/td&gt;&lt;td&gt;Wednesday, 8 October 2025 9:00 AM +13:00&lt;/td&gt;&lt;/tr&gt;
 &lt;tr&gt;&lt;td&gt;&lt;b&gt;Close date: &lt;/td&gt;&lt;td&gt;Monday, 31 December 2029 5:00 PM +13:00&lt;/td&gt;&lt;/tr&gt;
 &lt;tr&gt;&lt;td&gt;&lt;b&gt;Overview: &lt;/b&gt;&lt;/td&gt;&lt;td&gt;Panel of suppliers&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;</description>
</item></channel></rss>"""


def test_nouvelle_zelande():
    (item,) = nouvelle_zelande.extraire(NZ_RSS)
    assert item["id"] == "nz-32705858" and item["organisation"] == "MSD"
    assert item["date_limite"] == "2029-12-31" and item["date_publication"] == "2025-10-08"
    assert item["description"] == "Panel of suppliers"
    assert item["lien"] == "https://www.gets.govt.nz/MSD/ExternalTenderDetails.htm?id=32705858"



def test_wordpress():
    scraper = wordpress.MeddMadagascarScraper()
    article = {"id": 11595, "date": "2026-10-09T10:00:00", "link": "https://www.environnement.mg/appel-offre/ami/",
               "title": {"rendered": "AMI Recrutement d&rsquo;un prestataire"}}
    item = scraper.normalize(article)
    assert item["id"] == "medd-11595" and item["source"] == "medd" and item["pays"] == "Madagascar"
    assert item["titre"] == "AMI Recrutement d’un prestataire" and str(item["date_publication"]) == "2026-10-09"
    assert scraper.normalize(dict(article, title={"rendered": "Résultat de l'AMI"})) is None
    cemac = wordpress.CemacScraper().normalize(article)
    assert cemac["id"] == "cemac-11595" and cemac["source"] == "cemac" and cemac["pays"] == ""


Essais = en_cas_de_test(globals())
