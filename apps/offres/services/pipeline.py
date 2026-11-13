"""Pipeline de veille : collecte -> qualification -> persistance, en memoire.

Aucun fichier intermediaire : les ScrapedItem passent directement du scraper
au classifieur puis a l'ORM. La base fait foi pour savoir ce qui a deja ete vu.
"""

import re
from datetime import date

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from apps.offres.models import Offre
from apps.offres.scrapers import REGISTRE_SCRAPERS
from apps.offres.scrapers.unjobnet import enrichir_description
from apps.offres.services.classifier import RuleBasedClassifier
from apps.offres.services.notification import NotificationService
from apps.offres.services.taches import sans_suivi

MOIS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def en_date(valeur):
    """ISO ("2026-09-18", horodate ou non), "18 Sep 2026" (UNjobnet) ou date -> date | None.

    Une date mal lue ne doit pas devenir None en silence sur une source
    entiere : une offre sans echeance n'est jamais close avec certitude.
    """
    if isinstance(valeur, date):
        return valeur
    valeur = (valeur or "").strip()
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", valeur)
    if m and MOIS.get(m.group(2)[:3].lower()):
        annee, mois, jour = int(m.group(3)), MOIS[m.group(2)[:3].lower()], int(m.group(1))
    else:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", valeur)
        if not m:
            return None
        annee, mois, jour = map(int, m.groups())
    try:
        return date(annee, mois, jour)
    except ValueError:
        return None


def _texte(valeur, longueur=None):
    valeur = (str(valeur).strip() if valeur is not None else "") or None
    return valeur[:longueur] if valeur and longueur else valeur


def construire_offre(raw: dict) -> Offre:
    """ScrapedItem -> Offre qualifiee (non sauvegardee)."""
    verdict = RuleBasedClassifier.evaluer(raw)
    return Offre(
        id=raw["id"], source=raw["source"], titre=_texte(raw.get("titre")) or "(sans titre)",
        organisation=_texte(raw.get("organisation")),
        # Bornes des colonnes : un depassement ferait echouer tout le lot.
        pays=_texte(raw.get("pays"), 100), lien=_texte(raw.get("lien"), 2000),
        date_publication=en_date(raw.get("date_publication")),
        date_limite=en_date(raw.get("date_limite")),
        description=_texte(raw.get("description")),
        pertinent=verdict.pertinent, nature=verdict.nature, secteur=verdict.secteur,
        categorie=verdict.categorie, raison=verdict.raison,
    )


def _completer_descriptions(offres: list, progression=sans_suivi) -> None:
    """Fiche UNjobnet (~1.6 s chacune) chargee seulement pour les retenues."""
    a_completer = [o for o in offres
                   if o.source == "unjobnet" and not o.description and o.lien]
    for i, offre in enumerate(a_completer, start=1):
        progression(etape="Descriptions UNjobnet", courant=i, total=len(a_completer),
                    detail=offre.titre[:120])
        texte = enrichir_description(offre.lien)
        if texte:
            offre.description = texte
            Offre.objects.filter(pk=offre.pk).update(description=texte)


class PipelineService:

    CHAMPS_VERDICT = ["pertinent", "nature", "secteur", "categorie", "raison", "date_maj"]

    @classmethod
    def requalifier(cls, lot, progression=sans_suivi) -> dict:
        """Re-applique le classifieur sur des offres en base. Ne touche ni aux
        dates, ni au lien verifie, ni au suivi humain (table a part)."""
        from django.utils import timezone
        maintenant = timezone.now()
        total = retenues = changees = 0
        a_ecrire = []
        nombre = lot.count()
        progression(etape="Tri des offres", courant=0, total=nombre)
        for offre in lot.iterator(chunk_size=1000):
            v = RuleBasedClassifier.evaluer({"titre": offre.titre, "description": offre.description,
                                             "pays": offre.pays, "source": offre.source})
            avant = (offre.pertinent, offre.nature, offre.secteur, offre.categorie, offre.raison)
            apres = (v.pertinent, v.nature, v.secteur, v.categorie, v.raison)
            total += 1
            retenues += v.pertinent
            if total % 250 == 0:
                progression(courant=total, detail=f"{changees} verdict(s) modifié(s)")
            if avant != apres:
                changees += 1
                (offre.pertinent, offre.nature, offre.secteur,
                 offre.categorie, offre.raison) = apres
                offre.date_maj = maintenant   # bulk_update ignore auto_now
                a_ecrire.append(offre)
        Offre.objects.bulk_update(a_ecrire, cls.CHAMPS_VERDICT, batch_size=500)
        progression(courant=total, detail=f"{changees} verdict(s) modifié(s)")
        return {"total": total, "retenues": retenues, "changees": changees}

    @classmethod
    def executer(cls, complet: bool = False, source_filtre: str = None,
                 notifier: bool = True, progression=sans_suivi) -> list:
        deja_vus = set(Offre.objects.values_list("id", flat=True))
        connues = set(Offre.objects.values_list("source", flat=True).distinct())

        scrapers = REGISTRE_SCRAPERS
        if source_filtre:
            scrapers = [s for s in scrapers if s.source_key == source_filtre]
            if not scrapers:
                raise ValueError(f"Source inconnue : {source_filtre}")

        # Les trois etapes (collecte en memoire -> qualification -> ORM) sont
        # enchainees SOURCE PAR SOURCE : une collecte complete dure longtemps
        # (Crawl-delay de 10 s a la BAD), et tout garder pour la fin faisait
        # perdre l'ensemble a la moindre interruption.
        print(f"=== Collecte, qualification, enregistrement ({len(deja_vus)} ID(s) deja connus) ===")
        retenues, enregistrees = [], 0
        colonnes = (SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                    TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn())
        with Progress(*colonnes) as barre:
            tache = barre.add_task("Sources", total=len(scrapers))
            for i, scraper_cls in enumerate(scrapers):
                scraper = scraper_cls()
                barre.update(tache, description=scraper.nom)
                progression(etape=f"Collecte : {scraper.nom}", courant=i, total=len(scrapers),
                            detail=f"{enregistrees} offre(s) enregistrée(s), "
                                   f"{len(retenues)} retenue(s) jusqu'ici")
                neuve = scraper.source_key not in connues
                items = scraper.collecter(deja_vus, complet=complet, source_neuve=neuve)

                # Dedoublonnage : un id ne compte qu'une fois (le dernier gagne).
                par_id = {raw["id"]: raw for raw in items
                          if raw.get("id") and raw["id"] not in deja_vus}
                objets = [construire_offre(raw) for raw in par_id.values()]
                Offre.objects.bulk_create(objets, batch_size=500, ignore_conflicts=True)
                deja_vus.update(par_id)
                enregistrees += len(objets)
                retenues += [o for o in objets if o.pertinent]

                barre.console.print(f"  {scraper.nom} : {len(objets)} nouveaute(s), "
                                    f"{sum(o.pertinent for o in objets)} retenue(s)"
                                    + (" [plafond 1er lancement]" if neuve else ""))
                barre.advance(tache)
                progression(courant=i + 1, detail=f"{scraper.nom} : {len(objets)} nouveauté(s) — "
                                                   f"{enregistrees} enregistrée(s), {len(retenues)} retenue(s)")

        if not enregistrees:
            print("Aucune nouveaute detectee.")
            return []
        print(f"\n{enregistrees} offre(s) enregistree(s), {len(retenues)} retenue(s).")
        _completer_descriptions(retenues, progression)

        if notifier and retenues:
            try:
                NotificationService.envoyer_email(retenues)
            except Exception as exc:
                # Les offres sont deja en base : un email en echec ne fait pas echouer le run.
                print(f"Envoi de l'email echoue : {exc}")

        return retenues
