"""Tests du decoupage des resultats du portail marocain (PMMP).

Sans reseau ni dependance : `python test_maroc.py`.

Pieges constates le 14/09/2026 :

  - l'objet et le lieu sont repetes par une info-bulle dans la meme cellule ;
  - les elements de la ligne sont identifies d'apres le nom du champ cache
    refCons (ctl0$...$ctl7$refCons -> ctl0_..._ctl7_panelBlocObjet) ;
  - les boutons du formulaire ne doivent pas etre renvoyes dans un postback,
    seule la cible PRADO nomme la commande.
"""

from apps.offres.scrapers import maroc as m
from bs4 import BeautifulSoup

P = "ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch"
I = "ctl0_CONTENU_PAGE_resultSearch_tableauResultSearch"


def ligne(n, ref_cons, org, objet, acheteur, publie, cloture, ref="74/2026", procedure="Appel d'offres ouvert",
          categorie="Travaux", lieu="MAROC, TETOUAN"):
    return f'''<tr>
    <td class="check-col" headers="checkAll" style="display:none">
      <input name="{P}$ctl{n}$refCons" type="hidden" value="{ref_cons}"/>
      <input name="{P}$ctl{n}$orgCons" type="hidden" value="{org}"/></td>
    <td headers="cons_ref"><div class="line-info-bulle"> AOO <a class="info-suite">...</a></div>
      <div class="info-bulle" id="{I}_ctl{n}_panelBlocTypesProc"><div>{procedure}</div></div>
      <div id="{I}_ctl{n}_panelBlocCategorie">{categorie}</div><div>{publie}</div></td>
    <td headers="cons_intitule"><div class="objet-line"><span class="ref" id="{I}_ctl{n}_reference">{ref}</span></div>
      <div class="objet-line" id="{I}_ctl{n}_panelBlocObjet"><strong> Objet : </strong> {objet}
        <span class="info-suite" style="display:none">...</span>
        <div class="info-bulle"><div>{objet}</div></div></div>
      <div class="objet-line" id="{I}_ctl{n}_panelBlocDenomination"><strong> Acheteur public : </strong> {acheteur}</div></td>
    <td headers="cons_lieuExe"><div id="{I}_ctl{n}_panelBlocLieuxExec"> {lieu.replace(", ", "<br/>")}<br/>
      <div class="bloc-info-bulle"><a class="info-suite">...</a>
        <div class="info-bulle" id="{I}_ctl{n}_ctl15_infosLieuExecution"><div>{lieu}</div></div></div></div></td>
    <td headers="cons_dateEnd"><div><div class="cloture-line"> {cloture}<br/>10:00 </div></div></td>
    <td headers="cons_actions"><a href="?page=entreprise.EntrepriseDetailConsultation&amp;refConsultation={ref_cons}&amp;orgAcronyme={org}">
      <img alt="Accéder à la consultation"/></a></td></tr>'''


def page(*lignes):
    return BeautifulSoup(f'<form action="/index.php?page=x&amp;y" method="post"><input type="hidden" name="PRADO_PAGESTATE" value="abc"/>'
                         f'<table class="table-results">{"".join(lignes)}</table>'
                         f'<input type="submit" name="ctl0$bouton" value="Go"/><input type="checkbox" name="c1"/>'
                         f'<input type="checkbox" name="c2" checked="checked" value="oui"/>'
                         f'<select name="s"><option value="10">10</option><option value="100" selected="selected">100</option></select>'
                         f'</form>', "html.parser")


def test_decoupe_une_ligne():
    soup = page(ligne(1, "1038869", "d4q", "Renforcement de l'AEP", "ONEE", "11/09/2026", "04/11/2026"))
    lignes = m.lignes_de_la_page(soup)
    assert len(lignes) == 1
    l = lignes[0]
    assert l["ref_cons"] == "1038869" and l["org"] == "d4q"
    assert l["objet"] == "Renforcement de l'AEP", l["objet"]
    assert l["acheteur"] == "ONEE", l["acheteur"]
    assert l["lieu"] == "MAROC, TETOUAN", l["lieu"]
    assert l["publie"] == "11/09/2026" and l["cloture"].startswith("04/11/2026")
    assert l["procedure"] == "Appel d'offres ouvert" and l["categorie"] == "Travaux"


def test_normalisation():
    soup = page(ligne(7, "1025388", "s3z", "Acquisition des équipements", "Commune de Khemisset",
                      "12/09/2026", "30/10/2026", ref="17/2026", categorie="Fournitures", lieu="KHEMISSET"))
    item = m.normalize(m.lignes_de_la_page(soup)[0])
    assert item["id"] == "ma-1025388" and item["source"] == "maroc" and item["pays"] == "Maroc"
    assert item["titre"] == "Acquisition des équipements"
    assert item["organisation"] == "Commune de Khemisset"
    assert item["date_limite"] == "2026-10-30" and item["date_publication"] == "2026-09-12"
    assert item["description"] == ("Appel d'offres ouvert. Fournitures. Reference 17/2026. Lieu KHEMISSET. "
                                   "Acquisition des équipements"), item["description"]
    assert item["lien"] == ("https://www.marchespublics.gov.ma/index.php?page=entreprise."
                            "EntrepriseDetailConsultation&refConsultation=1025388&orgAcronyme=s3z"), item["lien"]


def test_champs_du_formulaire_comme_un_navigateur():
    action, champs = m.champs_du_formulaire(page())
    assert action == "https://www.marchespublics.gov.ma/index.php?page=x&y", action
    assert champs["PRADO_PAGESTATE"] == "abc"
    assert "ctl0$bouton" not in champs, "un bouton ne se renvoie pas"
    assert "c1" not in champs and champs["c2"] == "oui"
    assert champs["s"] == "100", "l'option selectionnee, pas la premiere"


def test_dates():
    assert m.date_iso("04/11/2026 10:00") == "2026-11-04"
    assert m.date_iso("") == "" and m.date_iso("31/02/2026") == ""


def test_page_sans_tableau():
    assert m.lignes_de_la_page(BeautifulSoup("<form></form>", "html.parser")) == []
    assert m.champs_du_formulaire(BeautifulSoup("<p>rien</p>", "html.parser")) == ("", {})


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
