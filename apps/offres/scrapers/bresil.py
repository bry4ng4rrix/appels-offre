"""Bresil, PNCP (Portail national des marches publics).

Source : API de consultation, avis publies sur une fenetre de dates pour un
mode de passation donne (le parametre est obligatoire). On ne garde que les
procedures concurrentielles (PREGAO / CONCORRENCIA electroniques) : la
"dispensa" et l'"inexigibilidade" sont des achats sans mise en concurrence.
"""

import time
from datetime import date, timedelta

from .base import BaseScraper
from .http import get_json
from Offre.sources import (PNCP_URL, PNCP_FICHE, PNCP_MODALITES, PNCP_FENETRE_JOURS,
                           PNCP_MAX_PAGES, PNCP_PAGE_DELAY, FIRST_RUN_MAX_ITEMS)

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}


def normalize(avis: dict) -> dict | None:
    orgao, unidade = avis.get("orgaoEntidade") or {}, avis.get("unidadeOrgao") or {}
    if not avis.get("numeroControlePNCP") or not avis.get("objetoCompra"):
        return None
    lieu = ", ".join(x for x in (unidade.get("municipioNome"), unidade.get("ufSigla")) if x)
    return {
        "id": f"br-{avis['numeroControlePNCP']}",
        "source": "bresil",
        "titre": avis["objetoCompra"].strip()[:500],
        "organisation": orgao.get("razaoSocial", ""),
        "pays": "Brésil",
        "date_limite": (avis.get("dataEncerramentoProposta") or "")[:10],
        "date_publication": (avis.get("dataPublicacaoPncp") or "")[:10],
        "description": ". ".join(x for x in (avis.get("modalidadeNome"), lieu,
                                             avis.get("informacaoComplementar") or "") if x),
        "lien": PNCP_FICHE.format(cnpj=orgao.get("cnpj", ""), ano=avis.get("anoCompra", ""),
                                  seq=avis.get("sequencialCompra", "")),
    }


class BresilScraper(BaseScraper):
    source_key = "bresil"
    nom = "Brésil (PNCP)"
    site = "https://pncp.gov.br/app/editais"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        aujourdhui = date.today()
        fenetre = {"dataInicial": (aujourdhui - timedelta(days=PNCP_FENETRE_JOURS)).strftime("%Y%m%d"),
                   "dataFinal": aujourdhui.strftime("%Y%m%d")}
        nouveaux, vus = [], set(seen_ids)
        for modalite in PNCP_MODALITES:
            for page in range(1, PNCP_MAX_PAGES + 1):
                time.sleep(PNCP_PAGE_DELAY)
                try:
                    reponse = get_json(PNCP_URL, HEADERS, {**fenetre, "pagina": page, "tamanhoPagina": 50,
                                                           "codigoModalidadeContratacao": modalite})
                except Exception as exc:
                    print(f"Brésil : modalite {modalite} page {page} en echec ({str(exc)[:60]}).")
                    break
                for item in filter(None, map(normalize, reponse.get("data") or [])):
                    if item["id"] not in vus and (not item["date_limite"]
                                                  or item["date_limite"] >= aujourdhui.isoformat()):
                        vus.add(item["id"])
                        nouveaux.append(item)
                if page >= (reponse.get("totalPaginas") or 0):
                    break
        return nouveaux[:limite] if limite else nouveaux
