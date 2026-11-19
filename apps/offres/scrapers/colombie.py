"""Colombie, SECOP II (Agence nationale Colombia Compra Eficiente).

Source : jeu de donnees ouvert "SECOP II - Procesos de Contratacion" sur
datos.gov.co (API Socrata, sans cle). On lit les procedures ouvertes publiees
dans la fenetre, hors modalites sans vraie concurrence : le "regimen
especial" (83 % du volume, surtout des contrats de personnes) et le gre a gre.
"""

from datetime import date, timedelta

from .base import BaseScraper
from .http import get_json
from Offre.sources import SECOP_URL, SECOP_FENETRE_JOURS, SECOP_MAX, FIRST_RUN_MAX_ITEMS

HEADERS = {"User-Agent": "veille-appels/1.0", "Accept": "application/json"}
EXCLUES = ("Contratación régimen especial", "Contratación régimen especial (con ofertas)",
           "Contratación directa", "Contratación Directa (con ofertas)",
           "Solicitud de información a los Proveedores")


def normalize(p: dict) -> dict | None:
    ident, titre = p.get("id_del_proceso"), (p.get("nombre_del_procedimiento") or "").strip()
    if not ident or not titre:
        return None
    lien = p.get("urlproceso")
    lien = lien.get("url", "") if isinstance(lien, dict) else (lien or "")
    lieu = ", ".join(x for x in (p.get("ciudad_entidad"), p.get("departamento_entidad")) if x)
    return {
        "id": f"co-{ident}",
        "source": "colombie",
        "titre": titre,
        "organisation": p.get("entidad", ""),
        "pays": "Colombie",
        "date_limite": "",
        "date_publication": (p.get("fecha_de_publicacion_del") or "")[:10],
        "description": ". ".join(x for x in (p.get("modalidad_de_contratacion"), p.get("tipo_de_contrato"),
                                             lieu, (p.get("descripci_n_del_procedimiento") or "")[:1200]) if x),
        "lien": lien,
    }


class ColombieScraper(BaseScraper):
    source_key = "colombie"
    nom = "Colombie (SECOP II)"
    site = "https://community.secop.gov.co/Public/Tendering/ContractNoticeManagement/Index"

    def scrape(self, seen_ids, complet=False):
        limite = None if complet or seen_ids else FIRST_RUN_MAX_ITEMS
        depuis = (date.today() - timedelta(days=SECOP_FENETRE_JOURS)).isoformat()
        exclues = ", ".join(f"'{m}'" for m in EXCLUES)
        lignes = get_json(SECOP_URL, HEADERS, {
            "$limit": SECOP_MAX, "$order": "fecha_de_publicacion_del DESC",
            "$where": (f"estado_de_apertura_del_proceso='Abierto' AND fecha_de_publicacion_del > '{depuis}' "
                       f"AND modalidad_de_contratacion NOT IN ({exclues})")}, timeout=90)
        vus, nouveaux = set(seen_ids), []
        for item in filter(None, map(normalize, lignes)):
            if item["id"] not in vus:
                vus.add(item["id"])
                nouveaux.append(item)
        return nouveaux[:limite] if limite else nouveaux
