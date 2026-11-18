"""Scraper UNGM, sans reseau : le balisage des gabarits est repris des reponses
reelles de www.ungm.org du 18/11/2026 (allegees des icones et des scripts)."""

from importlib import reload
from unittest import mock

import requests
from django.test import SimpleTestCase, TestCase, override_settings

from apps.offres import scrapers
from apps.offres.models import Offre
from apps.offres.scrapers import http, ungm as u
from apps.offres.services.pipeline import PipelineService

PAGE = ('<html><form><input name="__RequestVerificationToken" type="hidden" '
        'value="jeton-123" /></form></html>')


def ligne(nid, titre="Request for Quotations for the Airfares", echeance="24-Nov-2026 10:00",
          publie="18-Nov-2026", agence="ILO", nature="Request for quotation",
          ref="rfx_14498_ROAP", pays="Philippines"):
    return f"""
<div role="row" tabindex="0" data-noticeid="{nid}" class="tableRow dataRow notice-table">
    <div role="cell" class="tableCell editable intendbuttonsHeader resultOptions">
        <input type="button" value='Express Interest' class=btnEOI data-noticeid="{nid}" />
    </div>
    <div role="cell" class="tableCell resultTitle"><div class="ungm-flex-row">
        <span class="ungm-title ungm-title--small">
            {titre}
        </span>
        <a target='_blank' href='/Public/Notice/{nid}'></a></div>
    </div>
    <div role="cell" class="tableCell resultInfo1 deadline" data-description="Deadline">
        <span>

{echeance}
            (GMT 1.00)
        </span>
        <span class="remainingDaysToDeadline" style="display:none">6.13</span>
    </div>
    <div role="cell" class="tableCell"><span>

{publie}</span></div>
    <div role="cell" class="tableCell resultAgency"><span>{agence}</span></div>
    <div role="cell" class="tableCell"><span><label for='{nature}'>{nature}</label></span></div>
    <div role="cell" class="tableCell resultInfo1" data-description="Reference"><span>{ref}</span></div>
    <div role="cell" class="tableCell"><span>{pays}</span></div>
</div>
<script>var deadlineCells = document.querySelectorAll('.deadline span');</script>"""


def page_resultats(*ids):
    return "".join(ligne(i) for i in ids)


FICHE = """
<div class="ungm-list-item ungm-background">
    <div class="ungm-col-sm-12">
        <div class="row"><span class="label">Reference:</span>
            <span class="value">rfx_14498_ROAP</span></div>
        <div class="row"><span class="label">Beneficiary countries or territories:</span>
            <span class="value"> Philippines</span></div>
        <div class="row"><span class="label">Registration level:</span>
            <span class="value">Basic </span></div>
        <div class="row"><span class="label">Published on:</span>
            <span class="value">18-Nov-2026</span></div>
    </div>
</div>
<div class="ungm-list-item ungm-background">
    <div class="title">Description</div>
    <div> Dear Bidder,
The ILO is pleased to invite your company to submit an offer for this RFQ.</div>
</div>
<div class="docslist">
    <div class="filterDiv" data-documentid="2144845"><span class="selectedDocumentFilename">
        <a class="lnkShowDocument" href="/Public/Notice/DownloadDocument?noticeId=322896&amp;documentId=2144845">
            Annex 1-A Supplier User Guide.pdf
        </a></span></div>
</div>
<form method="post" action="/Public/Notice/DownloadAllDocuments?noticeId=322896"></form>
"""

UNSPSC = """<div class="unspscTree">
<div class="unspscNode" data-isparent="True" role=group><span class="nodeName  expanded filtered"><span class="floatLeft">78000000</span><span class="floatLeft">&nbsp;-&nbsp;</span><span class="floatLeft">Transportation Services</span></span>
<div class="unspscChildren">
<div class="unspscNode" data-isparent="True" role=group><span class="nodeName   "><span class="floatLeft">78203000</span><span class="floatLeft">&nbsp;-&nbsp;</span><span class="floatLeft">Airline Cabin And Support Services</span></span></div>
<div class="unspscNode" data-isparent="False" ><span class="nodeName   "><span class="floatLeft">78204002</span><span class="floatLeft">&nbsp;-&nbsp;</span><span class="floatLeft">Flight Operations Automation</span></span></div>
</div></div></div>"""


class Analyse(SimpleTestCase):

    def test_ligne_de_resultat(self):
        items, n = u.extraire(page_resultats(322896))
        self.assertEqual(n, 1)
        self.assertEqual(items[0], {
            "id": "ungm-322896", "source": "ungm",
            "titre": "Request for Quotations for the Airfares", "organisation": "ILO",
            "pays": "Philippines", "date_publication": "2026-11-18", "date_limite": "2026-11-24",
            "description": "Request for quotation. Reference rfx_14498_ROAP",
            "lien": "https://www.ungm.org/Public/Notice/322896"})

    def test_champs_manquants_et_dates_invalides(self):
        items, n = u.extraire(ligne(1, echeance="", publie="31-Feb-2026", ref="", pays="")
                              + ligne(2, titre="")                       # sans titre : ecartee
                              + '<div class="dataRow" data-noticeid="x"></div>')  # tronquee
        self.assertEqual(n, 3)
        self.assertEqual([i["id"] for i in items], ["ungm-1"])
        self.assertEqual((items[0]["date_limite"], items[0]["date_publication"], items[0]["pays"]),
                         ("", "", ""))
        self.assertEqual(items[0]["description"], "Request for quotation")

    def test_dates(self):
        self.assertEqual(u.date_ungm("24-Nov-2026 10:00 (GMT 1.00)"), "2026-11-24")
        for illisible in ("", None, "31-Feb-2026", "24/11/2026", "24-Foo-2026"):
            self.assertEqual(u.date_ungm(illisible), "")

    def test_jeton(self):
        self.assertEqual(u.jeton(PAGE), "jeton-123")
        with self.assertRaises(ValueError):
            u.jeton("<html></html>")

    def test_fiche_et_unspsc(self):
        fiche = u.lire_fiche(FICHE)
        self.assertEqual(fiche["champs"]["Registration level"], "Basic")
        self.assertTrue(fiche["description"].startswith("Dear Bidder,\nThe ILO"))
        self.assertEqual(fiche["documents"], [(
            "Annex 1-A Supplier User Guide.pdf",
            "https://www.ungm.org/Public/Notice/DownloadDocument?noticeId=322896&documentId=2144845")])
        self.assertEqual(u.lire_unspsc(UNSPSC), ["78203000 Airline Cabin And Support Services",
                                                 "78204002 Flight Operations Automation"])
        item = u.extraire(page_resultats(322896))[0][0]
        u.completer(item, fiche, u.lire_unspsc(UNSPSC))
        self.assertIn("Beneficiary countries or territories : Philippines", item["description"])
        self.assertIn("UNSPSC : 78203000", item["description"])
        self.assertIn("Annex 1-A Supplier User Guide.pdf <https://www.ungm.org/", item["description"])
        self.assertTrue(item["description"].endswith("submit an offer for this RFQ."))


class FauxSite:
    """Remplace get_html / post_html : 15 avis par page, ids decroissants."""

    def __init__(self, total, fiche_en_panne=()):
        self.ids = list(range(1000, 1000 - total, -1))
        self.pages, self.fiches, self.fiche_en_panne = [], [], set(fiche_en_panne)

    def get_html(self, url, headers, params=None, timeout=20, tentatives=3):
        if url == u.UNGM_URL:
            return PAGE
        if "/Unspscs/" in url:
            return UNSPSC
        numero = int(url.rsplit("/", 1)[1])
        self.fiches.append(numero)
        if numero in self.fiche_en_panne:
            raise requests.HTTPError("404")
        return FICHE

    def post_html(self, url, headers, corps, timeout=40, tentatives=3):
        assert headers["RequestVerificationToken"] == "jeton-123"
        p = corps["PageIndex"]
        self.pages.append(p)
        return page_resultats(*self.ids[p * 15:(p + 1) * 15])


@mock.patch.object(u.time, "sleep")
class Collecte(SimpleTestCase):

    def lancer(self, site, seen=(), complet=False):
        with mock.patch.object(u, "get_html", site.get_html), \
             mock.patch.object(u, "post_html", site.post_html):
            return u.UngmScraper().scrape(set(seen), complet=complet)

    def test_pagination_jusqu_a_la_derniere_page(self, _):
        site = FauxSite(40)
        items = self.lancer(site, seen={"autre-source-1"})
        self.assertEqual(site.pages, [0, 1, 2])
        self.assertEqual(len(items), 40)
        self.assertEqual(len({i["id"] for i in items}), 40)

    def test_incremental_s_arrete_a_la_premiere_page_connue(self, _):
        site = FauxSite(100)
        connus = {f"ungm-{i}" for i in site.ids[10:]}       # les 10 plus recents sont neufs
        items = self.lancer(site, seen=connus)
        self.assertEqual(site.pages, [0, 1])
        self.assertEqual([i["id"] for i in items], [f"ungm-{i}" for i in site.ids[:10]])
        self.assertEqual(site.fiches, site.ids[:10], "seules les fiches nouvelles sont lues")

    def test_complet_ignore_l_arret_anticipe(self, _):
        site = FauxSite(40)
        items = self.lancer(site, seen={f"ungm-{i}" for i in site.ids}, complet=True)
        self.assertEqual((site.pages, items), ([0, 1, 2], []))

    @mock.patch.object(u, "FIRST_RUN_MAX_ITEMS", 20)
    def test_plafond_de_premier_lancement(self, _):
        site = FauxSite(100)
        items = self.lancer(site)
        self.assertEqual((len(items), site.pages), (20, [0, 1]))

    def test_fiche_en_echec_garde_les_donnees_de_la_liste(self, _):
        site = FauxSite(2, fiche_en_panne={999})
        items = {i["id"]: i for i in self.lancer(site, seen={"x"})}
        self.assertIn("Dear Bidder", items["ungm-1000"]["description"])
        self.assertEqual(items["ungm-999"]["description"], "Request for quotation. Reference rfx_14498_ROAP")

    def test_panne_reseau_ecarte_la_source_sans_arreter_le_run(self, _):
        with mock.patch.object(u, "get_html", side_effect=requests.ConnectionError("hors ligne")):
            self.assertEqual(u.UngmScraper().collecter({"x"}), [])


class Reprise(SimpleTestCase):
    """post_html reprend sur erreur transitoire, avec repli exponentiel."""

    def reponse(self, code, texte=""):
        r = requests.Response()
        r.status_code, r._content = code, texte.encode()
        return r

    @mock.patch.object(http.time, "sleep")
    def test_503_puis_succes(self, dormir):
        faux = mock.Mock()
        faux.post.side_effect = [self.reponse(503), self.reponse(503), self.reponse(200, "ok")]
        with mock.patch.object(http, "session", return_value=faux):
            self.assertEqual(http.post_html("https://x", {}, {}), "ok")
        self.assertEqual([c.args[0] for c in dormir.call_args_list], [1, 2])

    @mock.patch.object(http.time, "sleep")
    def test_400_n_est_pas_retente(self, dormir):
        faux = mock.Mock()
        faux.post.return_value = self.reponse(400)
        with mock.patch.object(http, "session", return_value=faux):
            with self.assertRaises(requests.HTTPError):
                http.post_html("https://x", {}, {})
        self.assertEqual(faux.post.call_count, 1)
        dormir.assert_not_called()


class Registre(SimpleTestCase):

    def test_desactive_par_defaut_active_par_reglage(self):
        try:
            with override_settings(UNGM_ENABLED=False):
                self.assertNotIn("ungm", [s.source_key for s in reload(scrapers).REGISTRE_SCRAPERS])
            with override_settings(UNGM_ENABLED=True):
                self.assertIn("ungm", [s.source_key for s in reload(scrapers).REGISTRE_SCRAPERS])
        finally:
            reload(scrapers)


@mock.patch.object(u.time, "sleep")
@mock.patch("apps.offres.services.pipeline.REGISTRE_SCRAPERS", [u.UngmScraper])
class Persistance(TestCase):

    def test_enregistre_sans_doublon_au_second_passage(self, _):
        site = FauxSite(20)
        with mock.patch.object(u, "get_html", site.get_html), \
             mock.patch.object(u, "post_html", site.post_html):
            PipelineService.executer(notifier=False)
            self.assertEqual(Offre.objects.filter(source="ungm").count(), 20)
            site.pages.clear()
            PipelineService.executer(notifier=False)
        self.assertEqual(Offre.objects.filter(source="ungm").count(), 20)
        self.assertEqual(site.pages, [0], "second passage : une seule page lue")
        o = Offre.objects.get(pk="ungm-1000")
        self.assertEqual((o.organisation, o.pays, str(o.date_limite)), ("ILO", "Philippines", "2026-11-24"))
        self.assertEqual(o.lien, "https://www.ungm.org/Public/Notice/1000")
