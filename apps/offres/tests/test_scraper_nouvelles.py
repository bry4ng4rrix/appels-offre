"""Sources ajoutees le 17/11/2026 : PNUD, JIRAMA, Seychelles, BIsD. Sans reseau."""

from datetime import date, timedelta

from django.urls import reverse

from apps.offres.models import Offre
from apps.offres.scrapers import isdb, jirama, seychelles, undp
from apps.offres.tests.outils import AvecAdmin, en_cas_de_test

UNDP_HTML = """
<a class="vacanciesTableLink" href="view_negotiation.cfm?nego_id=51795">
 <div class="vacanciesTable__cell"><span>Supply of portable scanner</span></div>
 <div class="vacanciesTable__cell"><span>UNDP-BGD-01246</span></div>
 <div class="vacanciesTable__cell"><span>UNDP-MDG/MADAGASCAR</span></div>
 <div class="vacanciesTable__cell"><span>RFQ - Request for quotation</span></div>
 <div class="vacanciesTable__cell"><span><nobr>29-Nov-26 02:30 AM (New York time)</nobr></span></div>
 <div class="vacanciesTable__cell"><span><nobr>17-Nov-26</nobr></span></div>
</a>
<a class="vacanciesTableLink" href="view_notice.cfm?notice_id=98966">
 <div class="vacanciesTable__cell"><span>Appel a propositions</span></div>
 <div class="vacanciesTable__cell"><span>98966</span></div>
 <div class="vacanciesTable__cell"><span>CO BIH/BOSNIA AND HERZEGOVINA</span></div>
 <div class="vacanciesTable__cell"><span>Other</span></div>
 <div class="vacanciesTable__cell"><span>15-Dec-26</span></div>
 <div class="vacanciesTable__cell"><span>17-Nov-26</span></div>
</a>"""


def test_undp():
    a, b = undp.extraire(UNDP_HTML)
    assert a["id"] == "undp-51795" and b["id"] == "undp-n98966", "deux systemes, deux espaces d'id"
    assert a["pays"] == "Madagascar" and b["pays"] == "Bosnia And Herzegovina"
    assert a["date_limite"] == "2026-11-29" and a["date_publication"] == "2026-11-17"
    assert a["lien"] == "https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=51795"
    assert a["description"].startswith("RFQ - Request for quotation. Ref UNDP-BGD-01246.")


def test_jirama():
    article = {"id": 15722, "date": "2026-11-09T16:20:43", "link": "https://www.jirama.mg/avis/",
               "title": {"rendered": "Avis d&rsquo;Appel d&rsquo;Offres Ouvert N&deg; AO 98 351"}}
    item = jirama.normalize(article)
    assert item["id"] == "jirama-15722" and item["pays"] == "Madagascar"
    assert item["titre"] == "Avis d’Appel d’Offres Ouvert N° AO 98 351"
    assert item["date_publication"] == date(2026, 11, 9)
    for titre in ("Avis Rectificatif N°2 de l'AO 98 366", "Résultat de l'AO 98 300",
                  "Avis d'annulation de la CP 98 404"):
        assert jirama.normalize(dict(article, title={"rendered": titre})) is None, titre


SC_HTML = """
<div class="uk-article">
 <h2><a href="/tenders/civil-works/1864-construction-of-4-units">CONSTRUCTION OF 4 UNITS</a></h2>
 <time datetime="2026-11-16T08:00:46+04:00">Published: 16 November 2026</time>
 <script>var austDay = new Date('2026-11-30T10:00:00+04:00');</script>
</div>
<div class="uk-article"><h2>Sans lien</h2></div>"""


def test_seychelles():
    (item,) = seychelles.extraire(SC_HTML, "civil-works")
    assert item["id"] == "sc-1864" and item["pays"] == "Seychelles"
    assert item["date_limite"] == "2026-11-30" and item["date_publication"] == "2026-11-16"
    assert item["description"] == "Civil works. CONSTRUCTION OF 4 UNITS"
    assert item["lien"] == "https://www.pou.gov.sc/tenders/civil-works/1864-construction-of-4-units"


def _isdb(nid, statut, genre):
    return f"""<div class="views-row"><article data-nid="{nid}">
     <h2><a href="/project-procurement/tenders/2026/spn/avis-{nid}">Avis {nid}</a></h2>
     <div class="taxonomy-term vocabulary-tender-status slug-{statut}">x</div>
     <div class="taxonomy-term vocabulary-tender-type slug-{genre}">Specific Procurement Notice</div>
     <div class="field--name-field-world-country">Burkina Faso</div>
     <time datetime="00Z">16 December 2026</time></article></div>"""


def test_isdb():
    html = _isdb(1, "active", "spn") + _isdb(2, "closed", "spn") + _isdb(3, "active", "contract-award")
    avis, lus = isdb.extraire(html)
    assert lus == 3, "les articles lus comptent pour detecter la fin de liste"
    assert [a["id"] for a in avis] == ["isdb-1"], "seul l'avis actif, hors attribution"
    assert avis[0]["pays"] == "Burkina Faso" and avis[0]["date_limite"] == "2026-12-16"
    assert avis[0]["description"] == "Specific Procurement Notice. Avis 1"
    assert isdb.extraire("<html></html>") == ([], 0)


Essais = en_cas_de_test(globals())


class OngletSources(AvecAdmin):

    def test_les_sources_et_leur_bilan_sont_listees(self):
        Offre.objects.create(id="jirama-1", source="jirama", titre="AO", pays="Madagascar",
                             date_limite=date.today() + timedelta(days=9))
        page = self.client.get(reverse("web-parametres")).content.decode()
        self.assertIn('href="#sources"', page)
        self.assertIn("JIRAMA Madagascar", page)
        self.assertIn("www.jirama.mg", page)
        self.assertIn("PNUD (UNDP)", page)
        self.assertIn("Jamais", page, "source jamais collectee")
