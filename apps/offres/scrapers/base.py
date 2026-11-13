"""Contrat commun des scrapers.

Un scraper rend des ScrapedItem : de simples dictionnaires, que le pipeline
qualifie puis ecrit en base sans passer par aucun fichier intermediaire.
"""

from typing import TypedDict


class ScrapedItem(TypedDict, total=False):
    id: str                 # obligatoire, unique toutes sources confondues
    source: str             # obligatoire, = BaseScraper.source_key
    titre: str              # obligatoire
    organisation: str
    pays: str
    date_publication: str   # ISO, ou "18 Sep 2026" (UNjobnet) ; normalise par le pipeline
    date_limite: str
    description: str
    lien: str


class BaseScraper:
    #: Valeur du champ `source` en base. Sert aussi a detecter une source
    #: nouvellement branchee, pour lui appliquer le plafond de premier lancement.
    source_key: str = ""
    nom: str = ""

    def scrape(self, seen_ids: set, complet: bool = False) -> list[ScrapedItem]:
        raise NotImplementedError

    def collecter(self, deja_vus: set, complet: bool = False,
                  source_neuve: bool = False) -> list[ScrapedItem]:
        """Isole la source : une source en panne ne doit pas annuler le run.

        source_neuve : aucune offre de cette source en base. On passe alors un
        ensemble vide, ce qui declenche le plafond de premier lancement du
        scraper -- sans cela, la BAD avait remonte 802 avis au lieu de 100.
        """
        try:
            return self.scrape(set() if source_neuve else deja_vus, complet=complet)
        except Exception as exc:
            print(f"{self.nom} : echec ({exc}). Source ignoree pour ce run.")
            return []
