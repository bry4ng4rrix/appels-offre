"""Registre des scrapers et pipeline en memoire, sans reseau."""

from datetime import date
from unittest import mock

from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.offres.models import Offre, Suivi
from apps.offres.scrapers import REGISTRE_SCRAPERS
from apps.offres.scrapers.base import BaseScraper
from apps.offres.services.pipeline import PipelineService, en_date


class FauxScraper(BaseScraper):
    source_key = "faux"
    nom = "Faux"
    items = []
    recu = None

    def scrape(self, seen_ids, complet=False):
        FauxScraper.recu = set(seen_ids)
        return [i for i in self.items if i["id"] not in seen_ids]


class ScraperEnPanne(BaseScraper):
    source_key = "panne"
    nom = "En panne"

    def scrape(self, seen_ids, complet=False):
        raise ConnectionError("site injoignable")


def item(id_, titre, pays="Madagascar", **champs):
    return {"id": id_, "source": "faux", "titre": titre, "pays": pays, **champs}


class Registre(TestCase):

    def test_22_sources_aux_cles_uniques(self):
        cles = [s.source_key for s in REGISTRE_SCRAPERS]
        self.assertEqual(len(cles), 22)
        self.assertEqual(len(set(cles)), 22)
        for s in REGISTRE_SCRAPERS:
            with self.subTest(source=s.source_key):
                self.assertTrue(issubclass(s, BaseScraper) and s.nom)

    def test_une_source_en_panne_n_arrete_pas_le_run(self):
        self.assertEqual(ScraperEnPanne().collecter(set()), [])

    def test_une_source_neuve_recoit_un_ensemble_vide(self):
        FauxScraper.items = []
        FauxScraper().collecter({"x"}, source_neuve=True)
        self.assertEqual(FauxScraper.recu, set())


class Dates(TestCase):

    def test_formats_des_sources(self):
        self.assertEqual(en_date("2026-09-18"), date(2026, 9, 18))
        self.assertEqual(en_date("2026-09-18T10:00:00Z"), date(2026, 9, 18))
        self.assertEqual(en_date("18 Sep 2026"), date(2026, 9, 18))
        self.assertEqual(en_date(date(2026, 1, 2)), date(2026, 1, 2))
        for illisible in ("", None, "31/02/2026", "2026-02-31", "18 Foo 2026"):
            with self.subTest(valeur=illisible):
                self.assertIsNone(en_date(illisible))


@override_settings(NOTIFY_TO=["veille@example.org"])
@mock.patch("apps.offres.services.pipeline.enrichir_description", return_value="")
@mock.patch("apps.offres.services.pipeline.REGISTRE_SCRAPERS", [FauxScraper, ScraperEnPanne])
class Pipeline(TestCase):

    def setUp(self):
        FauxScraper.items = [
            item("f-1", "Développement d'une application mobile", date_limite="2026-12-01",
                 date_publication="20 Nov 2026"),
            item("f-2", "Fourniture de produits pharmaceutiques"),
            item("f-2", "Fourniture de produits pharmaceutiques (doublon)"),
            item("f-3", "Road rehabilitation", pays="Senegal", lien="https://x.org/" + "a" * 3000),
        ]

    def test_collecte_qualifie_et_persiste(self, *_):
        retenues = PipelineService.executer()
        self.assertEqual([o.id for o in retenues], ["f-1"])
        self.assertEqual(Offre.objects.count(), 3)
        f1 = Offre.objects.get(pk="f-1")
        self.assertEqual((f1.secteur, f1.nature, f1.pertinent), ("informatique", "marche", True))
        self.assertEqual((f1.date_limite, f1.date_publication), (date(2026, 12, 1), date(2026, 11, 20)))
        self.assertEqual(Offre.objects.get(pk="f-2").titre, "Fourniture de produits pharmaceutiques (doublon)")
        self.assertEqual(len(Offre.objects.get(pk="f-3").lien), 2000)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Développement d'une application mobile", mail.outbox[0].body)

    def test_un_second_passage_ne_reinsere_rien(self, *_):
        PipelineService.executer(notifier=False)
        self.assertEqual(PipelineService.executer(notifier=False), [])
        self.assertIn("f-1", FauxScraper.recu)
        self.assertEqual(Offre.objects.count(), 3)

    def test_filtre_par_source(self, *_):
        PipelineService.executer(source_filtre="faux", notifier=False)
        self.assertEqual(Offre.objects.count(), 3)
        with self.assertRaises(ValueError):
            PipelineService.executer(source_filtre="inconnue")

    def test_commande_veille(self, *_):
        call_command("veille", "--sans-notification", stdout=mock.MagicMock())
        self.assertEqual(Offre.objects.count(), 3)
        self.assertEqual(len(mail.outbox), 0)
        with self.assertRaises(CommandError):
            call_command("veille", "--source", "inconnue")


class ProgressionTemps(TestCase):

    def test_jauge(self):
        from datetime import timedelta
        from django.utils import timezone
        auj = timezone.now().date()
        self.assertEqual(Offre(date_limite=auj + timedelta(days=10),
                               date_publication=auj - timedelta(days=10)).progression_temps, 50)
        # Sans date de parution : fenetre de 30 jours, J-3 -> 90 %.
        self.assertEqual(Offre(date_limite=auj + timedelta(days=3)).progression_temps, 90)
        self.assertEqual(Offre(date_limite=auj + timedelta(days=60)).progression_temps, 0)
        self.assertEqual(Offre().progression_temps, 50)


class Requalification(TestCase):

    def test_corrige_le_verdict_sans_toucher_au_reste(self):
        o = Offre.objects.create(id="r-1", source="bad", titre="Construction d'un pont",
                                 pays="Madagascar", pertinent=False, secteur="autre",
                                 lien_etat="close", date_limite=date(2026, 12, 1))
        Suivi.objects.create(offre=o, statut=Suivi.CANDIDATURE)
        call_command("trier", stdout=mock.MagicMock())
        o.refresh_from_db()
        self.assertEqual((o.pertinent, o.secteur), (True, "construction"))
        self.assertEqual((o.lien_etat, o.date_limite), ("close", date(2026, 12, 1)))
        self.assertEqual(o.suivi.statut, Suivi.CANDIDATURE)

    def test_rien_a_changer(self):
        Offre.objects.create(id="r-2", source="bad", titre="Construction d'un pont", pays="Madagascar")
        self.assertEqual(PipelineService.requalifier(Offre.objects.all())["changees"], 1)
        self.assertEqual(PipelineService.requalifier(Offre.objects.all())["changees"], 0)


class Interrompu(BaseScraper):
    source_key = "coupe"
    nom = "Coupure"

    def scrape(self, seen_ids, complet=False):
        raise KeyboardInterrupt  # processus arrete en pleine collecte


class EnregistrementParSource(TestCase):

    @mock.patch("apps.offres.services.pipeline.REGISTRE_SCRAPERS", [FauxScraper, Interrompu])
    def test_une_interruption_garde_les_sources_deja_collectees(self):
        FauxScraper.items = [item("s-1", "Développement d'un logiciel")]
        with self.assertRaises(KeyboardInterrupt):
            PipelineService.executer(notifier=False)
        self.assertTrue(Offre.objects.filter(pk="s-1").exists())
