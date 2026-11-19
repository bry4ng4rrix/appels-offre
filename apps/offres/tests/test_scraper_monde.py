"""Quatrieme vague du 19/11/2026 : flux RSS/Atom, OCDS, Bresil, Colombie, organisations. Sans reseau."""

from apps.offres.scrapers import bresil, colombie, flux, ocds, organisations
from apps.offres.services.classifier import RuleBasedClassifier
from apps.offres.tests.outils import en_cas_de_test

RW_RSS = b"""<?xml version="1.0"?><rss><channel><item>
 <title>Logisticien</title><link>https://reliefweb.int/job/4238993/logisticien</link>
 <guid>https://reliefweb.int/job/4238993/logisticien</guid><pubDate>Thu, 19 Nov 2026 03:33:48 +0000</pubDate>
 <author>Pacific Community</author>
 <description>&lt;div&gt;Country: Madagascar&lt;/div&gt;&lt;div&gt;Organization: Pacific Community&lt;/div&gt;
 &lt;div&gt;Closing date: 10 Jan 2027&lt;/div&gt;&lt;p&gt;Description du poste&lt;/p&gt;</description>
</item></channel></rss>"""


def test_reliefweb():
    lues, suivante = flux.entrees(RW_RSS)
    assert suivante == ""
    item = flux.ReliefwebScraper().normalize(lues[0])
    assert item["id"] == "reliefweb-4238993" and item["pays"] == "Madagascar"
    assert item["date_limite"] == "2027-01-10" and item["date_publication"] == "2026-11-19"
    assert item["organisation"] == "Pacific Community"


def test_reliefweb_est_un_emploi():
    assert RuleBasedClassifier.detecter_nature("Logisticien", "reliefweb") == "emploi"


UY_RSS = """<?xml version="1.0"?><rss><channel><item>
 <title>Licitación Pública 29188/2027 - Administración Nacional de Puertos | Administración Nacional de Puertos</title>
 <link>https://www.comprasestatales.gub.uy/consultas/detalle/id/i500874</link>
 <guid>https://www.comprasestatales.gub.uy/consultas/detalle/id/i500874</guid>
 <pubDate>Tue, 08 Sep 2026 03:00:00 +0000</pubDate>
 <description>PROYECTO EJECUTIVO RECORTE ESPIGON A.&lt;br/&gt; Recepción de ofertas hasta: 17/03/2027 11:00hs&lt;br/&gt;Publicado</description>
</item></channel></rss>""".encode()


def test_uruguay():
    item = flux.UruguayScraper().normalize(flux.entrees(UY_RSS)[0][0])
    assert item["id"] == "uy-i500874" and item["titre"] == "PROYECTO EJECUTIVO RECORTE ESPIGON A."
    assert item["organisation"] == "Administración Nacional de Puertos"
    assert item["date_limite"] == "2027-03-17"
    assert item["description"].startswith("Licitación Pública 29188/2027.")


def _es(etat):
    return f"""<entry><id>https://contrataciondelestado.es/sindicacion/licitacionesPerfilContratante/{etat}1</id>
     <link href="https://contrataciondelestado.es/wps/poc?uri=x{etat}"/>
     <summary type="text">Id licitación: CBA5129/2026; Órgano de Contratación: Junta Centralizada; Importe: 23865 EUR; Estado: {etat}</summary>
     <title>Suministro de ordenadores</title><updated>2026-11-17T20:16:01.467+01:00</updated></entry>"""


def test_espagne():
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom"><link rel="next" href="https://x/suite.atom"/>'
           + _es("PUB") + _es("ADJ") + "</feed>").encode()
    lues, suivante = flux.entrees(xml)
    assert suivante == "https://x/suite.atom" and len(lues) == 2
    items = [i for i in map(flux.EspagneScraper().normalize, lues) if i]
    assert len(items) == 1, "un avis attribue (ADJ) n'est plus ouvert"
    assert items[0]["id"] == "es-PUB1" and items[0]["organisation"] == "Junta Centralizada"
    assert items[0]["date_publication"] == "2026-11-17"


def test_ocds_contracts_finder():
    release = {"ocid": "ocds-b5fd17-1", "date": "2026-11-18T18:10:03Z", "buyer": {"name": "Plus Dane Housing"},
               "tender": {"title": "Roof Terrace Refurbishment", "description": "Renewal of flat roofs",
                          "status": "active", "tenderPeriod": {"endDate": "2026-12-15T12:00:00Z"},
                          "documents": [{"documentType": "tenderNotice", "url": "https://cf/Notice/1"}]}}
    item = ocds.ContractsFinderScraper().normalize(release)
    assert item["id"] == "uk-ocds-b5fd17-1" and item["date_limite"] == "2026-12-15"
    assert item["lien"] == "https://cf/Notice/1" and item["organisation"] == "Plus Dane Housing"
    clos = dict(release, tender=dict(release["tender"], status="complete"))
    assert ocds.ContractsFinderScraper().normalize(clos) is None


def test_ocds_perou_titre_et_echeance():
    release = {"ocid": "ocds-dgv273-1", "date": "2026-11-18T10:23:13-05:00", "buyer": {"name": "Gobierno Regional"},
               "tender": {"title": "CP-ABR-2-2026-DREA/CS-2", "description": "CONTRATACIÓN DEL SERVICIO DE CONECTIVIDAD",
                          "tenderPeriod": {"endDate": "2026-11-17T00:00:00-05:00"},
                          "procurementMethodDetails": "Concurso Público Abreviado"}}
    item = ocds.PerouScraper().normalize(release)
    assert item["titre"] == "CONTRATACIÓN DEL SERVICIO DE CONECTIVIDAD", "la reference n'est pas un titre"
    assert item["date_limite"] == "", "endDate porte la publication au Perou"
    assert "Ref CP-ABR-2-2026-DREA/CS-2" in item["description"]


def test_ocds_paraguay_lien():
    release = {"ocid": "ocds-03ad3f-484367-1", "date": "2026-11-18T16:47:13-04:00",
               "tender": {"title": "Servicio médico", "tenderPeriod": {"endDate": "2026-11-27T09:15:00-04:00"}}}
    item = ocds.ParaguayScraper().normalize(release)
    assert item["lien"] == "https://www.contrataciones.gov.py/licitaciones/convocatoria/484367.html"
    assert item["date_limite"] == "2026-11-27"


def test_bresil():
    item = bresil.normalize({
        "numeroControlePNCP": "82765488000102-1-000015/2026", "objetoCompra": "Pavimentação de vias",
        "orgaoEntidade": {"cnpj": "82765488000102", "razaoSocial": "MUNICIPIO DE TAIO"},
        "unidadeOrgao": {"municipioNome": "Taió", "ufSigla": "SC"}, "anoCompra": 2026, "sequencialCompra": 15,
        "dataEncerramentoProposta": "2026-12-31T00:00:00", "dataPublicacaoPncp": "2026-11-18T10:00:00",
        "modalidadeNome": "Pregão - Eletrônico"})
    assert item["id"] == "br-82765488000102-1-000015/2026" and item["date_limite"] == "2026-12-31"
    assert item["lien"] == "https://pncp.gov.br/app/editais/82765488000102/2026/15"
    assert item["description"] == "Pregão - Eletrônico. Taió, SC"


def test_colombie():
    item = colombie.normalize({
        "id_del_proceso": "CO1.REQ.1", "nombre_del_procedimiento": "Mantenimiento de vías",
        "entidad": "Alcaldía", "ciudad_entidad": "Cali", "departamento_entidad": "Valle",
        "fecha_de_publicacion_del": "2026-11-17T22:33:31.672", "modalidad_de_contratacion": "Mínima cuantía",
        "urlproceso": {"url": "https://community.secop.gov.co/Public/Tendering/Opp"}})
    assert item["id"] == "co-CO1.REQ.1" and item["date_publication"] == "2026-11-17"
    assert item["lien"] == "https://community.secop.gov.co/Public/Tendering/Opp"
    assert item["description"].startswith("Mínima cuantía. Cali, Valle")


UNPD_HTML = """<li class="views-row"><div class="custom-card-title">EOIUNPD24917</div>
 <span class="start">18 Nov 2026</span><span class="end">02 Dec 2026</span>
 <div class="custom-card-title-field"><div>Interlocking Building Block System</div></div>
 <div class="eoi-commodity-group-field"><span class="field-content">Facility Management</span></div>
 <a href="https://www.ungm.org/Public/Notice/323017">Express Interest</a></li>"""


def test_onu_achats_partage_l_id_ungm():
    (item,) = organisations.OnuAchatsScraper().extraire(UNPD_HTML)
    assert item["id"] == "ungm-323017", "meme identifiant que le scraper UNGM : pas de doublon"
    assert item["date_limite"] == "2026-12-02" and item["date_publication"] == "2026-11-18"
    assert "Facility Management" in item["description"]


OSCE_HTML = """<article class="node--type-tender"><h4><a href="/tenders/provision-fuel-albania">Provision of Fuel</a></h4>
 <dl><dt>Launch date</dt><dd><time datetime="2026-11-11T12:00:00Z">11 November</time></dd>
 <dt>On behalf of</dt><dd><div>OSCE Presence in Albania</div></dd>
 <dt>Deadline</dt><dd><time datetime="2026-11-23T10:00:00Z">23 November</time></dd></dl></article>"""


def test_osce():
    (item,) = organisations.OsceScraper().extraire(OSCE_HTML)
    assert item["id"] == "osce-provision-fuel-albania" and item["organisation"] == "OSCE Presence in Albania"
    assert item["date_limite"] == "2026-11-23" and item["lien"] == "https://procurement.osce.org/tenders/provision-fuel-albania"


OPEC_HTML = """<table><tr><td>October 21, 2026</td><td>Costa Rica</td>
 <td><a href="https://publications.opecfund.org/view/781875507/">San José road</a></td><td>Transportation</td>
 <td>April 21, 2027 at 11:59 PM,(Costa Rica time)</td><td>International Competitive Bidding</td></tr></table>"""


def test_opec_fund():
    (item,) = organisations.OpecFundScraper().extraire(OPEC_HTML)
    assert item["id"] == "opec-781875507" and item["pays"] == "Costa Rica"
    assert item["date_limite"] == "2027-04-21", "l'annee ne doit pas etre coupee"
    assert item["date_publication"] == "2026-10-21"


def test_tri_espagnol_portugais():
    evaluer = RuleBasedClassifier.evaluer
    assert evaluer({"titre": "Adquisición de medicamentos", "pays": "Paraguay"}).secteur == "sante"
    assert evaluer({"titre": "Pavimentação asfáltica de vias", "pays": "Brésil"}).secteur == "construction"
    assert evaluer({"titre": "Desarrollo de software de gestión", "pays": "Colombie"}).secteur == "informatique"
    assert evaluer({"titre": "Construction d'un pont", "pays": "Madagascar"}).secteur == "construction"


Essais = en_cas_de_test(globals())
