# Instructions de Construction : Projet Django Unifié "Appels d'Offres"

Ce document constitue la **feuille de route technique complète et le prompt de référence** pour que Claude reconstruise et migre l'intégralité du projet de veille (`/home/garrix/Dev/veille-appels`) vers ce dossier `/home/garrix/Dev/appels-offre`.

---

## 1. Principes Fondamentaux de la Refonte

1. **Mono-Projet Django 100% Autonome** :
   - Fini la séparation entre scripts racine et sous-dossier `backend/`.
   - Tout le code (scrapers, qualification, persistance, commandes CLI, API et web UI) vit dans l'application Django unique `apps/offres`.
2. **Suppression Totale des Fichiers CSV & JSON de Travail** :
   - Le flux ne passe plus par `data/collecte.csv` ni `data/collecte.json`.
   - La collecte s'exécute directement en mémoire (objets Python `ScrapedItem`) et s'insère directement dans la base de données PostgreSQL via l'ORM Django.
3. **Suppression d'Ollama et Remplacement par du Code Pur (Étape 2)** :
   - Aucun LLM local (`qwen3:4b`), aucune dépendance lourde, zéro consommation GPU.
   - La qualification (Nature: marché/emploi, Secteur, Géographie, Pertinence) est confiée à un moteur de règles déterministe en Python pur (`RuleBasedClassifier`), ultra-rapide (< 1 ms par offre, soit 2 secondes pour 2 000 offres au lieu de 6 heures).
4. **Schéma Django Natif (`managed = True`)** :
   - Le modèle `Offre` appartient pleinement à Django et gère ses propres migrations.
   - Vraies contraintes de clés étrangères entre `Offre` et `Suivi`.
5. **Design Minimaliste mais Présentable (Style Linear / Shadcn UI / GitHub)** :
   - Interface moderne avec **Tailwind CSS**, mode clair/sombre, typographie soignée et bordures douces.
   - **Barres de progression** (jauge d'échéance par offre, barres statistiques de conversion, barre de progression CLI avec `rich`).
   - **Animations fluides** (transitions au survol, pulsation sur urgences imminentes, toasts de notification animés, spinners d'attente).
   - **Boutons pour TOUTES les actions** (synchronisation, re-tri, changement de statut commercial en 1 clic sans rechargement de page via AJAX/HTMX, modification d'échéance).

---

## 2. Arborescence du Projet Préparée

Le dossier a été préparé avec la structure suivante :

```text
/home/garrix/Dev/appels-offre/
├── manage.py                      # Point d'entrée Django opérationnel
├── requirements.txt               # Dépendances Python
├── .env.example                   # Exemple de configuration
├── docker-compose.yml             # Conteneur PostgreSQL (port 5433)
├── instructions.md                # Ce document de spécification
│
├── Offre/                         # Configuration centrale du projet Django
│   ├── __init__.py
│   ├── settings.py                # Paramètres globaux + constantes
│   ├── urls.py                    # Routage central
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── __init__.py
│   └── offres/                    # Application Django unifiée
│       ├── __init__.py
│       ├── apps.py                # Configuration de l'app (OffresConfig)
│       ├── models.py              # Modèles Offre, Suivi, CleApi (managed=True)
│       ├── admin.py               # Interface d'administration
│       ├── urls.py                # Routes web et API
│       ├── views_web.py           # Interface web avec session
│       ├── views_api.py           # API privée avec jeton SHA-256
│       ├── views_public.py        # API publique (lecture seule)
│       │
│       ├── scrapers/              # Les 22 scrapers unifiés
│       │   ├── __init__.py        # Registre REGISTRE_SCRAPERS
│       │   ├── base.py            # BaseScraper & ScrapedItem
│       │   ├── http.py            # Client HTTP avec reprise sur erreur (backoff)
│       │   ├── banquemondiale.py
│       │   ├── bad.py
│       │   ├── armp_madagascar.py
│       │   ├── unjobnet.py
│       │   ├── ted.py
│       │   ├── boamp.py
│       │   ├── conservation.py
│       │   └── ... (toutes les autres sources nationales)
│       │
│       ├── services/              # Logique métier pure
│       │   ├── __init__.py
│       │   ├── classifier.py      # Moteur de règles en code pur (Remplace Ollama)
│       │   ├── pipeline.py        # Orchestrateur : Collecte -> Tri -> Persistance ORM
│       │   ├── lien_checker.py    # Détection des offres closes / 404
│       │   ├── notification.py    # Envoi d'emails récapitulatifs (SMTP)
│       │   └── geo.py             # Normalisation des pays, coordonnées et régions
│       │
│       ├── management/
│       │   ├── __init__.py
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── veille.py          # Commande principale tout-en-un
│       │       ├── trier.py           # Re-qualification rapide de la base
│       │       ├── verifier_liens.py  # Contrôle HTTP des offres
│       │       ├── envoyer_recap.py   # Envoi direct du récapitulatif
│       │       └── cle_api.py         # Création et révocation de clés d'API
│       │
│       ├── tests/                 # Tests unitaires sans réseau
│       │   ├── __init__.py
│       │   ├── test_classifier.py
│       │   └── test_scrapers.py
│       │
│       └── migrations/
│           └── __init__.py
│
├── templates/                     # Templates HTML / SVG de l'interface
│   ├── base.html
│   ├── registration/
│   │   └── login.html
│   └── offres/
│       ├── liste.html
│       ├── detail.html
│       ├── carte.html
│       ├── suivi.html
│       └── a_dater.html
│
├── static/                        # Fichiers CSS / JS
│   ├── css/
│   │   └── styles.css
│   └── js/
│
└── deploiement/                   # Gunicorn, Dockerfile, Systemd
```

---

## 3. Correspondance des Fichiers (Ancien Projet -> Nouveau Projet)

| Ancien fichier (`veille-appels/`) | Nouveau fichier cible (`appels-offre/`) | Rôle & Action à mener |
|---|---|---|
| `backend/offres/models.py` | `apps/offres/models.py` | Transformer `managed = False` en `managed = True`, vraies `ForeignKey`. |
| `config.py` + `backend/config/settings.py` | `Offre/settings.py` | Fusionner les constantes (URLs, délais, headers) dans les settings Django. |
| `backend/offres/admin.py` | `apps/offres/admin.py` | Rebrancher avec filtres d'échéances et de pertinence. |
| `backend/offres/views.py` | `apps/offres/views_api.py` | Endpoints API avec authentification par jeton. |
| `backend/offres/views_public.py` | `apps/offres/views_public.py` | Endpoints API publics en lecture seule. |
| `backend/offres/vues_web.py` | `apps/offres/views_web.py` | Vues de l'interface utilisateur web. |
| `backend/offres/coordonnees.py` + `regions.py` | `apps/offres/services/geo.py` | Coordonnées GPS pour la carte et régions. |
| `web.py` | `apps/offres/scrapers/http.py` | Client HTTP réutilisable avec retry exponentiel. |
| `triage.py` | `apps/offres/services/classifier.py` | **Remplacement d'Ollama** par des regex/règles de classification. |
| `main.py` + `etape1` + `etape2` + `etape3` | `apps/offres/services/pipeline.py` & `management/commands/veille.py` | Pipeline unique en 3 étapes directes en mémoire. |
| `retrier.py` | `apps/offres/management/commands/trier.py` | Re-tri ultra-rapide de la base. |
| `verifier_liens.py` | `apps/offres/management/commands/verifier_liens.py` | Vérificateur de vie des URLs sources. |
| `notify.py` | `apps/offres/services/notification.py` | Service d'envoi d'email via `django.core.mail`. |
| `scraper_*.py` (22 fichiers) | `apps/offres/scrapers/*.py` | Transformer en classes héritant de `BaseScraper`. |
| `test_*.py` (17 fichiers) | `apps/offres/tests/*.py` | Tests unitaires utilisant `django.test.TestCase`. |
| `backend/templates/` | `templates/` | Templates modernisés avec Tailwind CSS et HTMX. |

---

## 4. Spécifications Techniques Détaillées

### 4.1. Modèles (`apps/offres/models.py`)

```python
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
PRESUMEE_CLOSE_JOURS = 30


class Offre(models.Model):
    NATURE_CHOICES = [
        ("marche", "Marché"),
        ("emploi", "Emploi"),
    ]
    SECTEUR_CHOICES = [
        ("informatique", "Informatique"),
        ("construction", "Construction"),
        ("agriculture", "Agriculture"),
        ("eau", "Eau"),
        ("environnement", "Environnement"),
        ("autre", "Autre"),
    ]
    LIEN_ETAT_CHOICES = [
        ("ouverte", "En ligne"),
        ("introuvable", "Retirée (404)"),
        ("close", "Annoncée close"),
        ("illisible", "Illisible"),
    ]

    id = models.CharField(max_length=255, primary_key=True)
    source = models.CharField(max_length=100, db_index=True)
    titre = models.TextField()
    organisation = models.TextField(null=True, blank=True)
    pays = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    date_publication = models.DateField(null=True, blank=True, db_index=True)
    date_limite = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    lien = models.URLField(max_length=2000, null=True, blank=True)

    # Qualification par le moteur de règles
    pertinent = models.BooleanField(default=False, db_index=True)
    nature = models.CharField(max_length=20, choices=NATURE_CHOICES, null=True, blank=True)
    secteur = models.CharField(max_length=30, choices=SECTEUR_CHOICES, null=True, blank=True, db_index=True)
    categorie = models.CharField(max_length=255, null=True, blank=True)
    raison = models.TextField(null=True, blank=True)

    # État du lien source
    lien_verifie_le = models.DateTimeField(null=True, blank=True)
    lien_etat = models.CharField(max_length=20, choices=LIEN_ETAT_CHOICES, null=True, blank=True, db_index=True)

    # Métadonnées
    date_ajout = models.DateTimeField(auto_now_add=True, db_index=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offres"
        ordering = ["-date_ajout"]
        verbose_name = "Offre"
        verbose_name_plural = "Offres"

    def __str__(self):
        return f"[{self.source}] {self.titre[:70]}"

    @property
    def jours_restants(self):
        if not self.date_limite:
            return None
        return (self.date_limite - timezone.now().date()).days

    @property
    def est_ouverte(self) -> bool:
        if self.lien_etat in ("introuvable", "close"):
            return False
        if self.date_limite:
            return self.date_limite >= timezone.now().date()
        date_ref = self.date_publication or self.date_ajout.date()
        return (timezone.now().date() - date_ref).days <= PRESUMEE_CLOSE_JOURS

    @property
    def progression_temps(self) -> int:
        """Pourcentage de temps écoulé entre la publication et l'échéance (pour la barre de progression)."""
        if not self.date_publication or not self.date_limite:
            return 50
        total = (self.date_limite - self.date_publication).days
        if total <= 0:
            return 100
        ecoule = (timezone.now().date() - self.date_publication).days
        return max(0, min(100, int((ecoule / total) * 100)))


class CleApi(models.Model):
    PREFIXE = "veille_"
    nom = models.CharField(max_length=80, unique=True)
    empreinte = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    derniere_utilisation = models.DateTimeField(null=True, blank=True, editable=False)
    revoque_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cles_api"
        ordering = ["-cree_le"]


class Suivi(models.Model):
    STATUT_CHOICES = [
        ("a_etudier", "À étudier"),
        ("candidature", "Candidature déposée"),
        ("gagne", "Gagné"),
        ("perdu", "Perdu"),
        ("hors_sujet", "Hors sujet"),
    ]
    offre = models.OneToOneField(Offre, on_delete=models.CASCADE, related_name="suivi")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="a_etudier", db_index=True)
    note = models.TextField(blank=True)
    echeance = models.DateField(null=True, blank=True)
    echeance_saisie_le = models.DateTimeField(null=True, blank=True)
    decide_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    decide_par_cle = models.ForeignKey(CleApi, null=True, blank=True, on_delete=models.SET_NULL)
    cree_le = models.DateTimeField(auto_now_add=True)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suivi"
        ordering = ["-maj_le"]
```

---

### 4.2. Moteur de Tri en Code Pur (`apps/offres/services/classifier.py`)

Ce service remplace Ollama. Il exécute les règles métiers sous forme de regex et de scoring :

```python
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Verdict:
    pertinent: bool
    nature: str
    secteur: str
    categorie: str
    raison: str


class RuleBasedClassifier:
    EMPLOI_KEYWORDS = [
        r"\bcomptable\b", r"\bchauffeur\b", r"\bingenieur\b", r"\bassistant\b",
        r"\bcoordonnateur\b", r"\bcoordinateur\b", r"\bchercheur\b", r"\bdeveloppeur\b",
        r"\banalyste\b", r"\bcharge de\b", r"\bresponsable\b", r"\bconsultant individuel\b",
        r"\bindividual consultant\b", r"\bvacancy\b", r"\bjob announcement\b",
        r"\brecrutement d['’]un\b"
    ]
    MARCHE_KEYWORDS = [
        r"\bfirme\b", r"\bcabinet\b", r"\bfourniture\b", r"\btravaux\b",
        r"\bprestation\b", r"\bacquisition\b", r"\bselection d['’]une societe\b",
        r"\bselection d['’]une firme\b", r"\bconsulting firm\b"
    ]

    SECTEURS = {
        "informatique": [
            r"logiciel", r"software", r"developpement web", r"web development",
            r"systeme d['’]information", r"information system", r"erp", r"crm",
            r"base de donnees", r"database", r"numerisation", r"digitalis",
            r"transformation numerique", r"materiel informatique", r"it equipment",
            r"serveur", r"reseau informatique", r"call center", r"centre d['’]appels",
            r"bpo", r"support client", r"marketing digital", r"seo", r"siteweb",
            r"application mobile", r"cloud", r"cybersecurite"
        ],
        "eau": [
            r"adduction d['’]eau", r"water supply", r"forage", r"drilling",
            r"chateau d['’]eau", r"potabilisation", r"station de pompage",
            r"pumping station", r"assainissement", r"sanitation", r"sewerage",
            r"eaux usees", r"wastewater", r"drainage", r"wash", r"hydraulique"
        ],
        "environnement": [
            r"gestion des dechets", r"waste management", r"biodiversite",
            r"biodiversity", r"aire protegee", r"conservation", r"reforestation",
            r"changement climatique", r"climate change", r"resilience", r"carbone",
            r"etude d['’]impact environnemental", r"eies", r"esia",
            r"energie renouvelable", r"solaire", r"solar", r"eolien", r"depollution"
        ],
        "agriculture": [
            r"production agricole", r"semence", r"seed", r"intrant",
            r"elevage", r"livestock", r"peche", r"fisheries", r"aquaculture",
            r"irrigation", r"hydro-agricole", r"genie rural", r"chaine de valeur",
            r"securite alimentaire", r"food security", r"sylviculture"
        ],
        "construction": [
            r"batiment", r"building", r"genie civil", r"civil works",
            r"travaux publics", r"voirie", r"route", r"road", r"pont", r"bridge",
            r"rehabilitation", r"extension", r"terrassement", r"second oeuvre",
            r"electricite", r"plomberie", r"materiaux de construction"
        ],
    }

    PRIORITES_SECTEUR = ["informatique", "eau", "environnement", "agriculture", "construction"]
    PAYS_OCEAN_INDIEN = {"madagascar", "reunion", "la reunion", "mayotte", "maurice", "comores", "seychelles"}

    @classmethod
    def normaliser_texte(cls, texte: str) -> str:
        t = (texte or "").lower()
        accents = str.maketrans("àâäéèêëîïôöûüùçñ", "aaaeeeeiioouuucn")
        return t.translate(accents)

    @classmethod
    def detecter_nature(cls, titre: str, description: str) -> str:
        texte = cls.normaliser_texte(titre)
        for pattern in cls.EMPLOI_KEYWORDS:
            if re.search(pattern, texte):
                return "emploi"
        for pattern in cls.MARCHE_KEYWORDS:
            if re.search(pattern, texte):
                return "marche"
        return "marche"

    @classmethod
    def detecter_secteur(cls, texte: str) -> tuple[str, Optional[str]]:
        for secteur in cls.PRIORITES_SECTEUR:
            for pattern in cls.SECTEURS[secteur]:
                m = re.search(pattern, texte)
                if m:
                    return secteur, m.group(0)
        return "autre", None

    @classmethod
    def evaluer(cls, item: dict) -> Verdict:
        titre = item.get("titre") or ""
        desc = item.get("description") or ""
        pays = (item.get("pays") or "").lower().strip()
        texte = cls.normaliser_texte(f"{titre} {desc}")

        nature = cls.detecter_nature(titre, desc)
        secteur, match_word = cls.detecter_secteur(texte)

        if secteur == "autre":
            return Verdict(pertinent=False, nature=nature, secteur="autre",
                           categorie="Hors périmètre", raison="Aucun mot-clé ciblé")

        est_mg = "madagascar" in pays or pays == "mg"
        est_ocean_indien = est_mg or any(p in pays for p in cls.PAYS_OCEAN_INDIEN)

        if est_mg:
            pertinent = True
            raison = f"Cible Madagascar ({match_word})"
        elif secteur == "informatique":
            pertinent = True
            raison = f"IT télétravaillable ({match_word})"
        elif est_ocean_indien:
            pertinent = True
            raison = f"Zone Océan Indien ({match_word})"
        else:
            pertinent = False
            raison = f"Hors zone géographique pour {secteur}"

        categorie = f"{secteur.capitalize()} - {nature.capitalize()}"
        return Verdict(pertinent=pertinent, nature=nature, secteur=secteur,
                       categorie=categorie, raison=raison[:60])
```

---

### 4.3. Pipeline d'Ingestion Directe en 3 Étapes (`apps/offres/services/pipeline.py`)

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from apps.offres.models import Offre
from apps.offres.scrapers import REGISTRE_SCRAPERS
from apps.offres.services.classifier import RuleBasedClassifier
from apps.offres.services.notification import NotificationService


class PipelineService:

    @classmethod
    def executer(cls, complet: bool = False, source_filtre: str = None, notifier: bool = True):
        deja_vus = set(Offre.objects.values_list("id", flat=True))
        nouvelles_offres = []
        offres_retenues = []

        scrapers = REGISTRE_SCRAPERS
        if source_filtre:
            scrapers = [s for s in scrapers if s.source_key == source_filtre]

        # ÉTAPE 1 : Collecte en mémoire (pas de CSV !)
        print("=== Étape 1 : Collecte ===")
        for scraper_cls in scrapers:
            scraper = scraper_cls()
            items = scraper.collecter(deja_vus=deja_vus, complet=complet)
            nouvelles_offres.extend(items)

        if not nouvelles_offres:
            print("Aucune nouveauté détectée.")
            return []

        # ÉTAPE 2 : Tri et qualification par le Code (instantané)
        print(f"\n=== Étape 2 : Qualification de {len(nouvelles_offres)} offres ===")
        objets = []
        for raw in nouvelles_offres:
            verdict = RuleBasedClassifier.evaluer(raw)
            offre = Offre(
                id=raw["id"], source=raw["source"], titre=raw["titre"],
                organisation=raw.get("organisation"), pays=raw.get("pays"),
                date_publication=raw.get("date_publication"),
                date_limite=raw.get("date_limite"), description=raw.get("description"),
                lien=raw.get("lien"), pertinent=verdict.pertinent,
                nature=verdict.nature, secteur=verdict.secteur,
                categorie=verdict.categorie, raison=verdict.raison
            )
            objets.append(offre)
            if verdict.pertinent:
                offres_retenues.append(offre)

        # ÉTAPE 3 : Persistance ORM directe et notifications
        print(f"\n=== Étape 3 : Sauvegarde ORM ({len(objets)} insérées, {len(offres_retenues)} retenues) ===")
        Offre.objects.bulk_create(objets, ignore_conflicts=True)

        if notifier and offres_retenues:
            NotificationService.envoyer_email(offres_retenues)

        return offres_retenues
```

---

## 5. Spécifications du Front-End (UI/UX, Barres de Progression, Animations et Boutons)

1. **Framework CSS & Scripts** :
   - Inclure **Tailwind CSS** (via CDN moderne `@tailwindcss/browser` ou compile) pour un style épuré.
   - Inclure **HTMX** (`https://unpkg.com/htmx.org`) pour exécuter les actions des boutons sans rechargement de page.

2. **Composants d'Action Directe (Boutons pour TOUT)** :
   - **En-tête supérieur** :
     - Bouton `[ Actualiser / Veille ]` avec icône spinner.
     - Bouton `[ Re-classifier ]`.
     - Bouton `[ Vérifier les liens ]`.
     - Bouton `[ Exporter ]` (menu déroulant JSON / CSV).
     - Bouton `[ Copier le récapitulatif ]`.
   - **Cartes d'offres** :
     - Bouton primaire `Consulter l'annonce officielle` (icône lien externe).
     - Boutons de changement de statut en 1 clic : `[ À étudier ]`, `[ Candidater ]`, `[ Gagné ]`, `[ Perdu ]`, `[ Hors sujet ]`.
     - Bouton `[ Modifier l'échéance ]` (ouvre une modale rapide).
     - Bouton `[ Copier le lien ]`.

3. **Barres de Progression et Animations** :
   - Mini jauge temporelle sur chaque offre indiquant le délai restant (Vert > 15j, Orange 7-15j, Rouge < 7j).
   - Pastille animée (`animate-pulse`) sur les échéances sous 3 jours.
   - Effet de survol doux sur les cartes (`hover:-translate-y-0.5 hover:shadow-md transition-all duration-200`).
   - Toasts de notification animés en bas d'écran lors des clics sur les boutons.

---

## 6. Ordre d'Exécution pour Claude

Lorsque vous lancez Claude dans ce dossier `/home/garrix/Dev/appels-offre`, donnez-lui la commande suivante :

> *"Claude, lis attentivement le fichier `instructions.md` situé dans ce dossier.
> Reconstruis l'ensemble du projet en suivant fidèlement les 6 sections :
> 1. Adapte `Offre/settings.py` (configuration PostgreSQL port 5433, activation de `apps.offres`, templates et statiques).
> 2. Implémente `apps/offres/models.py` avec `managed = True` et les clés étrangères réelles.
> 3. Implémente le moteur de règles sans LLM `apps/offres/services/classifier.py`.
> 4. Porte le client HTTP résilient dans `apps/offres/scrapers/http.py` et les 22 scrapers depuis `/home/garrix/Dev/veille-appels/scraper_*.py` vers `apps/offres/scrapers/`.
> 5. Implémente le pipeline direct `apps/offres/services/pipeline.py` et les commandes de management (`veille`, `trier`, `verifier_liens`, `envoyer_recap`, `cle_api`).
> 6. Crée les templates HTML dans `templates/` avec Tailwind CSS et HTMX en appliquant le design minimaliste, les barres de progression temporelles, les animations fluides et les boutons d'action en 1 clic.
> 7. Rebranche les vues web et API dans `apps/offres/`.
> 8. Exécute les migrations initiales (`python manage.py makemigrations offres` puis `python manage.py migrate`).
> 9. Vérifie le bon fonctionnement avec `python manage.py check`."*
