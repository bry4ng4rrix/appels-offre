"""Sources ajoutees le 19/11/2026 : UE Funding & Tenders, Grants.gov, Ouganda, Cote d'Ivoire. Sans reseau."""

from apps.offres.scrapers import cote_ivoire, grants_gov, ouganda, ue_ft
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


Essais = en_cas_de_test(globals())
