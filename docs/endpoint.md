# Endpoints — Label Collectes

Serveur : `http://157.173.103.147:8001` (en local : `http://localhost:8000`).

Ce fichier est généré depuis le schéma OpenAPI de l'API (`/api/v1/schema/`). Les champs, types et codes ci-dessous sont donc ceux du serveur.

## Démarrage rapide

1. **Se connecter** :

   ```http
   POST /_allauth/app/v1/auth/login
   Content-Type: application/json

   {"email": "nom@exemple.org", "password": "..."}
   ```

   La réponse contient `meta.session_token`.

2. **Appeler l'API** en envoyant ce jeton dans l'en-tête `X-Session-Token`, à chaque appel :

   ```bash
   curl -H "X-Session-Token: <jeton>" http://157.173.103.147:8001/api/v1/moi/
   ```

3. **Se déconnecter** : `DELETE /_allauth/app/v1/auth/session` (avec le même en-tête).

**Accès** :

| Mention | Ce qu'il faut |
|---|---|
| Public | rien |
| Connecté | l'en-tête `X-Session-Token` |
| Admin | le jeton d'un compte admin (`is_staff`) |
| Clé machine | l'en-tête `X-API-Key: veille_...` (API des scripts, section 4) |

**Erreurs** : toujours `{"erreur": "message"}`. Une saisie invalide ajoute
`"champs": {"nom_du_champ": ["message"]}`.

| Code | Sens |
|---|---|
| 400 | Saisie invalide |
| 401 | Jeton absent, expiré ou inconnu : renvoyer à la connexion |
| 402 | Plus de crédits (`code: "credits_epuises"`) |
| 403 | Réservé aux admins |
| 404 | Introuvable |
| 409 | Conflit : demande déjà en attente, tâche déjà en cours |
| 429 | Trop d'appels : réessayer après l'en-tête `Retry-After` |

**Pagination** : `?page=2&par_page=50` (100 au plus). Réponse :
`{"total", "page", "pages", "par_page", "resultats": [...]}`.

**Envoi de fichiers** (CV, photo) : en `multipart/form-data`. Tout le reste en JSON.

## Sommaire

| Méthode | Route | Accès |
|---|---|---|
| | **1. Connexion** `/_allauth/app/v1/` | |
| POST | [`/_allauth/app/v1/auth/login`](#connexion) | Public |
| POST | [`/_allauth/app/v1/auth/signup`](#connexion) | Public |
| GET | [`/_allauth/app/v1/auth/session`](#connexion) | Connecté |
| DELETE | [`/_allauth/app/v1/auth/session`](#connexion) | Connecté |
| POST | [`/_allauth/app/v1/auth/password/request`](#connexion) | Public |
| POST | [`/_allauth/app/v1/auth/password/reset`](#connexion) | Public |
| POST | [`/_allauth/app/v1/account/password/change`](#connexion) | Connecté |
| POST | [`/_allauth/app/v1/auth/provider/token`](#connexion) | Public |
| | **2. API des applis** `/api/v1/` | |
| GET | [`/api/v1/abonnements/`](#get-api-v1-abonnements) | Connecté |
| POST | [`/api/v1/abonnements/`](#post-api-v1-abonnements) | Connecté |
| GET | [`/api/v1/admin/{catalogue}/`](#get-api-v1-admin-catalogue) | Admin |
| POST | [`/api/v1/admin/{catalogue}/`](#post-api-v1-admin-catalogue) | Admin |
| PATCH | [`/api/v1/admin/{catalogue}/{objet_id}/`](#patch-api-v1-admin-catalogue-objet-id) | Admin |
| DELETE | [`/api/v1/admin/{catalogue}/{objet_id}/`](#delete-api-v1-admin-catalogue-objet-id) | Admin |
| POST | [`/api/v1/admin/{catalogue}/{objet_id}/basculer/`](#post-api-v1-admin-catalogue-objet-id-basculer) | Admin |
| GET | [`/api/v1/admin/abonnements/`](#get-api-v1-admin-abonnements) | Admin |
| POST | [`/api/v1/admin/abonnements/{abonnement_id}/refuser/`](#post-api-v1-admin-abonnements-abonnement-id-refuser) | Admin |
| POST | [`/api/v1/admin/abonnements/{abonnement_id}/valider/`](#post-api-v1-admin-abonnements-abonnement-id-valider) | Admin |
| GET | [`/api/v1/admin/cles/`](#get-api-v1-admin-cles) | Admin |
| POST | [`/api/v1/admin/cles/`](#post-api-v1-admin-cles) | Admin |
| DELETE | [`/api/v1/admin/cles/{cle_id}/`](#delete-api-v1-admin-cles-cle-id) | Admin |
| GET | [`/api/v1/admin/exporter/`](#get-api-v1-admin-exporter) | Admin |
| POST | [`/api/v1/admin/offres/{offre_id}/decision/`](#post-api-v1-admin-offres-offre-id-decision) | Admin |
| POST | [`/api/v1/admin/offres/{offre_id}/echeance/`](#post-api-v1-admin-offres-offre-id-echeance) | Admin |
| POST | [`/api/v1/admin/offres/{offre_id}/verdict/`](#post-api-v1-admin-offres-offre-id-verdict) | Admin |
| GET | [`/api/v1/admin/parametres/`](#get-api-v1-admin-parametres) | Admin |
| POST | [`/api/v1/admin/parametres/collecte/`](#post-api-v1-admin-parametres-collecte) | Admin |
| POST | [`/api/v1/admin/parametres/email/`](#post-api-v1-admin-parametres-email) | Admin |
| POST | [`/api/v1/admin/parametres/email/tester/`](#post-api-v1-admin-parametres-email-tester) | Admin |
| POST | [`/api/v1/admin/parametres/pertinence/`](#post-api-v1-admin-parametres-pertinence) | Admin |
| GET | [`/api/v1/admin/plans/`](#get-api-v1-admin-plans) | Admin |
| POST | [`/api/v1/admin/plans/`](#post-api-v1-admin-plans) | Admin |
| GET | [`/api/v1/admin/plans/{plan_id}/`](#get-api-v1-admin-plans-plan-id) | Admin |
| PUT | [`/api/v1/admin/plans/{plan_id}/`](#put-api-v1-admin-plans-plan-id) | Admin |
| PATCH | [`/api/v1/admin/plans/{plan_id}/`](#patch-api-v1-admin-plans-plan-id) | Admin |
| GET | [`/api/v1/admin/sources/`](#get-api-v1-admin-sources) | Admin |
| GET | [`/api/v1/admin/statistiques/`](#get-api-v1-admin-statistiques) | Admin |
| GET | [`/api/v1/admin/suivi/`](#get-api-v1-admin-suivi) | Admin |
| GET | [`/api/v1/admin/taches/`](#get-api-v1-admin-taches) | Admin |
| GET | [`/api/v1/admin/taches/{tache_id}/`](#get-api-v1-admin-taches-tache-id) | Admin |
| POST | [`/api/v1/admin/taches/{tache_id}/{action}/`](#post-api-v1-admin-taches-tache-id-action) | Admin |
| POST | [`/api/v1/admin/taches/lancer/{nom}/`](#post-api-v1-admin-taches-lancer-nom) | Admin |
| POST | [`/api/v1/admin/taches/toutes/{action}/`](#post-api-v1-admin-taches-toutes-action) | Admin |
| GET | [`/api/v1/carte/points/`](#get-api-v1-carte-points) | Connecté |
| GET | [`/api/v1/moi/`](#get-api-v1-moi) | Connecté |
| GET | [`/api/v1/notifications/`](#get-api-v1-notifications) | Connecté |
| GET | [`/api/v1/offres/`](#get-api-v1-offres) | Connecté |
| GET | [`/api/v1/offres/{offre_id}/`](#get-api-v1-offres-offre-id) | Connecté |
| POST | [`/api/v1/offres/{offre_id}/consulter/`](#post-api-v1-offres-offre-id-consulter) | Connecté |
| GET | [`/api/v1/plans/`](#get-api-v1-plans) | Public |
| GET | [`/api/v1/pour-vous/`](#get-api-v1-pour-vous) | Connecté |
| GET | [`/api/v1/profil/`](#get-api-v1-profil) | Connecté |
| GET | [`/api/v1/profil/cv/`](#get-api-v1-profil-cv) | Connecté |
| POST | [`/api/v1/profil/cv/`](#post-api-v1-profil-cv) | Connecté |
| DELETE | [`/api/v1/profil/cv/`](#delete-api-v1-profil-cv) | Connecté |
| PUT | [`/api/v1/profil/domaines/`](#put-api-v1-profil-domaines) | Connecté |
| PUT | [`/api/v1/profil/perso/`](#put-api-v1-profil-perso) | Connecté |
| GET | [`/api/v1/profil/photo/`](#get-api-v1-profil-photo) | Connecté |
| PUT | [`/api/v1/profil/preferences/`](#put-api-v1-profil-preferences) | Connecté |
| PUT | [`/api/v1/profil/pro/`](#put-api-v1-profil-pro) | Connecté |
| GET | [`/api/v1/reference/`](#get-api-v1-reference) | Public |
| GET | `/api/v1/schema/`, `/api/v1/docs/` | Admin (public si DEBUG) |
| | **3. API publique** `/api/public/` | Public |
| | **4. API machine** `/api/` | Clé machine |

## 1. Connexion

<a id="connexion"></a>
Servie par django-allauth. Les applis (Next.js côté serveur, Flutter) utilisent le
client `app` ; toutes les routes commencent par `/_allauth/app/v1/`. Le détail complet
est dans `/_allauth/openapi.html`.

| Méthode | Route | Corps | Rôle |
|---|---|---|---|
| POST | `/_allauth/app/v1/auth/login` | `{"email", "password"}` | Connexion ; renvoie `meta.session_token` |
| POST | `/_allauth/app/v1/auth/signup` | `{"email", "password"}` | Inscription ; renvoie aussi un jeton |
| GET | `/_allauth/app/v1/auth/session` | — | L'utilisateur connecté (200) ou 401 |
| DELETE | `/_allauth/app/v1/auth/session` | — | Déconnexion |
| POST | `/_allauth/app/v1/auth/password/request` | `{"email"}` | Envoie l'email « mot de passe oublié » |
| GET | `/_allauth/app/v1/auth/password/reset` | en-tête `X-Password-Reset-Key` | Vérifie la clé reçue par email |
| POST | `/_allauth/app/v1/auth/password/reset` | `{"key", "password"}` | Nouveau mot de passe |
| POST | `/_allauth/app/v1/account/password/change` | `{"current_password", "new_password"}` | Changer de mot de passe (connecté) |
| POST | `/_allauth/app/v1/auth/provider/token` | `{"provider": "google", "process": "login", "token": {"client_id", "id_token"}}` | Connexion Google depuis l'appli (jeton obtenu par le SDK Google) |
| GET | `/_allauth/app/v1/config` | — | Options actives (Google, inscription...) |

Réponse type d'une connexion réussie :

```json
{
  "status": 200,
  "data": {"user": {"id": 3, "email": "nom@exemple.org", "display": "..."}, "methods": [...]},
  "meta": {"is_authenticated": true, "session_token": "j8x...Qa"}
}
```

Un mauvais mot de passe renvoie 400 avec `errors: [{"message", "code", "param"}]`
(format d'allauth, différent de celui de `/api/v1/`).

## 2. API des applis (`/api/v1/`)

Toutes les routes demandent l'en-tête `X-Session-Token`, sauf mention « Public ». Les routes `/api/v1/admin/` répondent 403 à un utilisateur simple.

### Utilisateur

<a id="get-api-v1-abonnements"></a>
#### GET /api/v1/abonnements/

**Accès : Connecté** — GET\|POST /api/v1/abonnements/ — mes demandes et crédits ; demander un plan.

Réponse **200** ([MesAbonnements](#objet-mesabonnements)) :

| Champ | Type | Note |
|---|---|---|
| `credits` | [Credits](#objet-credits) |  |
| `abonnements` | liste de [Abonnement](#objet-abonnement) |  |

<a id="post-api-v1-abonnements"></a>
#### POST /api/v1/abonnements/

**Accès : Connecté** — GET\|POST /api/v1/abonnements/ — mes demandes et crédits ; demander un plan.

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `plan` | entier | oui | id d'un plan proposé. |

Réponse **201** ([DemandeCreee](#objet-demandecreee)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `abonnement` | [Abonnement](#objet-abonnement) |  |

Erreurs : 409, 400, 401, 403, 404, 429.

### Administration

<a id="get-api-v1-admin-catalogue"></a>
#### GET /api/v1/admin/{catalogue}/

**Accès : Admin** — GET\|POST /api/v1/admin/<secteurs\|pays>/ — le catalogue avec le nombre d'offres ; ajouter {"nom"}.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `catalogue` | chemin | `pays` \| `secteurs` |  |

Réponse **200** :

Type : liste de [Catalogue](#objet-catalogue)

<a id="post-api-v1-admin-catalogue"></a>
#### POST /api/v1/admin/{catalogue}/

**Accès : Admin** — GET\|POST /api/v1/admin/<secteurs\|pays>/ — le catalogue avec le nombre d'offres ; ajouter {"nom"}.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `catalogue` | chemin | `pays` \| `secteurs` |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | oui | (max 100 car.) |

Réponse **201** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="patch-api-v1-admin-catalogue-objet-id"></a>
#### PATCH /api/v1/admin/{catalogue}/{objet_id}/

**Accès : Admin** — PATCH\|DELETE /api/v1/admin/<secteurs\|pays>/<id>/ — renommer {"nom"} ; retirer des choix (les offres restent).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `catalogue` | chemin | `pays` \| `secteurs` |  |
| `objet_id` | chemin | entier |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | non | (max 100 car.) |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="delete-api-v1-admin-catalogue-objet-id"></a>
#### DELETE /api/v1/admin/{catalogue}/{objet_id}/

**Accès : Admin** — PATCH\|DELETE /api/v1/admin/<secteurs\|pays>/<id>/ — renommer {"nom"} ; retirer des choix (les offres restent).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `catalogue` | chemin | `pays` \| `secteurs` |  |
| `objet_id` | chemin | entier |  |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-catalogue-objet-id-basculer"></a>
#### POST /api/v1/admin/{catalogue}/{objet_id}/basculer/

**Accès : Admin** — activer ou désactiver dans les filtres.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `catalogue` | chemin | `pays` \| `secteurs` |  |
| `objet_id` | chemin | entier |  |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-abonnements"></a>
#### GET /api/v1/admin/abonnements/

**Accès : Admin** — toutes les demandes d'abonnement.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `page` | requête | entier |  |
| `par_page` | requête | entier | 100 au plus. |
| `statut` | requête | `attente` \| `refuse` \| `valide` |  |

Réponse **200** ([PageAbonnementsAdmin](#objet-pageabonnementsadmin)) :

| Champ | Type | Note |
|---|---|---|
| `en_attente` | entier |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [AbonnementAdmin](#objet-abonnementadmin) |  |

<a id="post-api-v1-admin-abonnements-abonnement-id-refuser"></a>
#### POST /api/v1/admin/abonnements/{abonnement_id}/refuser/

**Accès : Admin** — refuse une demande en attente.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `abonnement_id` | chemin | entier |  |

Réponse **200** ([AbonnementAdmin](#objet-abonnementadmin)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `plan` | [PlanCourt](#objet-plancourt) |  |
| `statut` | `attente` \| `valide` \| `refuse` |  |
| `statut_libelle` | texte |  |
| `etat` | texte | attente, refuse, actif ou termine. |
| `demande_le` | date-heure |  |
| `debut` | date ou null |  |
| `fin` | date ou null | Dernier jour inclus ; null : sans fin. |
| `credits_jour` | entier |  |
| `credits_restants` | entier |  |
| `utilisateur` | [UtilisateurCourt](#objet-utilisateurcourt) |  |
| `valide_par` | texte ou null |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-abonnements-abonnement-id-valider"></a>
#### POST /api/v1/admin/abonnements/{abonnement_id}/valider/

**Accès : Admin** — paiement reçu : les crédits sont actifs.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `abonnement_id` | chemin | entier |  |

Réponse **200** ([AbonnementAdmin](#objet-abonnementadmin)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `plan` | [PlanCourt](#objet-plancourt) |  |
| `statut` | `attente` \| `valide` \| `refuse` |  |
| `statut_libelle` | texte |  |
| `etat` | texte | attente, refuse, actif ou termine. |
| `demande_le` | date-heure |  |
| `debut` | date ou null |  |
| `fin` | date ou null | Dernier jour inclus ; null : sans fin. |
| `credits_jour` | entier |  |
| `credits_restants` | entier |  |
| `utilisateur` | [UtilisateurCourt](#objet-utilisateurcourt) |  |
| `valide_par` | texte ou null |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-cles"></a>
#### GET /api/v1/admin/cles/

**Accès : Admin** — GET\|POST /api/v1/admin/cles/ — clés d'API machine ; en créer une (le jeton n'est montré qu'une fois).

Réponse **200** :

Type : liste de [Cle](#objet-cle)

<a id="post-api-v1-admin-cles"></a>
#### POST /api/v1/admin/cles/

**Accès : Admin** — GET\|POST /api/v1/admin/cles/ — clés d'API machine ; en créer une (le jeton n'est montré qu'une fois).

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | oui | (max 100 car.) |

Réponse **201** ([CleCreee](#objet-clecreee)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `jeton` | texte | Montré une seule fois : seule son empreinte est gardée. |

Erreurs : 400, 401, 403, 404, 429.

<a id="delete-api-v1-admin-cles-cle-id"></a>
#### DELETE /api/v1/admin/cles/{cle_id}/

**Accès : Admin** — révoque une clé machine.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `cle_id` | chemin | entier |  |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-exporter"></a>
#### GET /api/v1/admin/exporter/

**Accès : Admin** — la sélection (mêmes filtres que la liste) en CSV ou JSON.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `date_a` | requête | date | Échéance jusqu'à. |
| `date_de` | requête | date | Échéance à partir de. |
| `etat` | requête | `actionnables` \| `cloturees` \| `ecartees` \| `retenues` \| `retirees` \| `sans-echeance` \| `toutes` | Onglet (défaut : toutes = ouvertes). |
| `format` | requête | `csv` \| `json` |  |
| `lieu` | requête | texte | Lieu exact, tel que la carte le donne. |
| `nature` | requête | `emploi` \| `inconnue` \| `marche` |  |
| `pays` | requête | texte | Code de /reference/ pays. |
| `q` | requête | texte | Titre, organisation ou catégorie. |
| `region` | requête | `afrique` \| `ameriques` \| `asie-pacifique` \| `europe` \| `inconnue` \| `international` \| `madagascar` \| `moyen-orient` \| `ocean-indien` |  |
| `secteur` | requête | texte | Code de /reference/ secteurs. |

Réponse **200** : le fichier (`text/csv`).

<a id="post-api-v1-admin-offres-offre-id-decision"></a>
#### POST /api/v1/admin/offres/{offre_id}/decision/

**Accès : Admin** — pose ou change le statut commercial.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `offre_id` | chemin | texte |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` | oui |  |
| `note` | texte ou null | non | Absente : inchangée ; vide : effacée. (max 2000 car.) |

Réponse **200** ([Suivi](#objet-suivi)) :

| Champ | Type | Note |
|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` |  |
| `statut_libelle` | texte |  |
| `note` | texte |  |
| `echeance` | date ou null |  |
| `echeance_saisie_le` | date-heure ou null |  |
| `decide_par` | texte ou null |  |
| `decide_par_cle` | texte ou null |  |
| `maj_le` | date-heure |  |

Réponse **201** ([Suivi](#objet-suivi)) :

| Champ | Type | Note |
|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` |  |
| `statut_libelle` | texte |  |
| `note` | texte |  |
| `echeance` | date ou null |  |
| `echeance_saisie_le` | date-heure ou null |  |
| `decide_par` | texte ou null |  |
| `decide_par_cle` | texte ou null |  |
| `maj_le` | date-heure |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-offres-offre-id-echeance"></a>
#### POST /api/v1/admin/offres/{offre_id}/echeance/

**Accès : Admin** — saisit l'échéance qu'une source ne publie pas.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `offre_id` | chemin | texte |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `echeance` | date | oui |  |

Réponse **200** ([Suivi](#objet-suivi)) :

| Champ | Type | Note |
|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` |  |
| `statut_libelle` | texte |  |
| `note` | texte |  |
| `echeance` | date ou null |  |
| `echeance_saisie_le` | date-heure ou null |  |
| `decide_par` | texte ou null |  |
| `decide_par_cle` | texte ou null |  |
| `maj_le` | date-heure |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-offres-offre-id-verdict"></a>
#### POST /api/v1/admin/offres/{offre_id}/verdict/

**Accès : Admin** — corrige le verdict du tri (retenue ou écartée).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `offre_id` | chemin | texte |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `pertinent` | booléen | oui |  |

Réponse **200** ([Verdict](#objet-verdict)) :

| Champ | Type | Note |
|---|---|---|
| `pertinent` | booléen |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-parametres"></a>
#### GET /api/v1/admin/parametres/

**Accès : Admin** — collecte, email (sans mot de passe), pondération, sources.

Réponse **200** ([Parametres](#objet-parametres)) :

| Champ | Type | Note |
|---|---|---|
| `collecte` | [ParametresCollecte](#objet-parametrescollecte) |  |
| `email` | [ParametresEmail](#objet-parametresemail) |  |
| `pertinence` | liste de [Pertinence](#objet-pertinence) |  |
| `sources` | liste de [SourceParametre](#objet-sourceparametre) |  |

<a id="post-api-v1-admin-parametres-collecte"></a>
#### POST /api/v1/admin/parametres/collecte/

**Accès : Admin** — fréquence de la collecte et heure de la nuit.

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `intervalle_collecte` | entier | oui | (min 1) |
| `heure_nuit` | texte | non | HH:MM |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-parametres-email"></a>
#### POST /api/v1/admin/parametres/email/

**Accès : Admin** — serveur SMTP et destinataires (mot de passe vide = inchangé).

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `smtp_hote` | texte | non | Vide : serveur du .env. (max 255 car.) |
| `smtp_port` | entier ou null | non | (min 1) |
| `smtp_securite` | `tls` \| `ssl` \| `aucune` | non |  |
| `smtp_utilisateur` | texte | non |  |
| `smtp_mot_de_passe` | texte | non | Vide : inchangé. |
| `destinataires` | liste de texte | non |  |

Réponse **200** ([EmailEnregistre](#objet-emailenregistre)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `mot_de_passe_efface` | booléen |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-parametres-email-tester"></a>
#### POST /api/v1/admin/parametres/email/tester/

**Accès : Admin** — envoie un email de test.

Réponse **200** ([EmailTest](#objet-emailtest)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `niveau` | `succes` \| `info` |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-parametres-pertinence"></a>
#### POST /api/v1/admin/parametres/pertinence/

**Accès : Admin** — pondération du score de correspondance (0 à 100).

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `competences` | entier | oui | Compétences (min 0) |
| `domaine` | entier | oui | Domaine (secteur) (min 0) |
| `categorie` | entier | oui | Catégorie (min 0) |
| `localisation` | entier | oui | Localisation (min 0) |
| `mots_cles` | entier | oui | Mots-clés (min 0) |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-plans"></a>
#### GET /api/v1/admin/plans/

**Accès : Admin** — GET\|POST /api/v1/admin/plans/ — tous les plans ; en créer un.

Réponse **200** :

Type : liste de [Plan](#objet-plan)

<a id="post-api-v1-admin-plans"></a>
#### POST /api/v1/admin/plans/

**Accès : Admin** — GET\|POST /api/v1/admin/plans/ — tous les plans ; en créer un.

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | oui | (max 60 car.) |
| `prix` | entier | oui | (min 0) |
| `credits` | entier | oui | (min 1) |
| `par_jour` | booléen | non | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | non | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen | non |  |

Réponse **201** ([Plan](#objet-plan)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 60 car.) |
| `prix` | entier | (min 0) |
| `credits` | entier | (min 1) |
| `par_jour` | booléen | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen |  |
| `prix_credit` | entier | Prix d'un credit, pour comparer les plans. |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-plans-plan-id"></a>
#### GET /api/v1/admin/plans/{plan_id}/

**Accès : Admin** — GET\|PUT\|PATCH /api/v1/admin/plans/<id>/ — un plan ; le modifier (les abonnements validés gardent leurs crédits).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `plan_id` | chemin | entier |  |

Réponse **200** ([Plan](#objet-plan)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 60 car.) |
| `prix` | entier | (min 0) |
| `credits` | entier | (min 1) |
| `par_jour` | booléen | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen |  |
| `prix_credit` | entier | Prix d'un credit, pour comparer les plans. |

<a id="put-api-v1-admin-plans-plan-id"></a>
#### PUT /api/v1/admin/plans/{plan_id}/

**Accès : Admin** — GET\|PUT\|PATCH /api/v1/admin/plans/<id>/ — un plan ; le modifier (les abonnements validés gardent leurs crédits).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `plan_id` | chemin | entier |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | oui | (max 60 car.) |
| `prix` | entier | oui | (min 0) |
| `credits` | entier | oui | (min 1) |
| `par_jour` | booléen | non | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | non | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen | non |  |

Réponse **200** ([Plan](#objet-plan)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 60 car.) |
| `prix` | entier | (min 0) |
| `credits` | entier | (min 1) |
| `par_jour` | booléen | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen |  |
| `prix_credit` | entier | Prix d'un credit, pour comparer les plans. |

Erreurs : 400, 401, 403, 404, 429.

<a id="patch-api-v1-admin-plans-plan-id"></a>
#### PATCH /api/v1/admin/plans/{plan_id}/

**Accès : Admin** — GET\|PUT\|PATCH /api/v1/admin/plans/<id>/ — un plan ; le modifier (les abonnements validés gardent leurs crédits).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `plan_id` | chemin | entier |  |

Corps (`application/json`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `nom` | texte | non | (max 60 car.) |
| `prix` | entier | non | (min 0) |
| `credits` | entier | non | (min 1) |
| `par_jour` | booléen | non | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | non | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen | non |  |

Réponse **200** ([Plan](#objet-plan)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 60 car.) |
| `prix` | entier | (min 0) |
| `credits` | entier | (min 1) |
| `par_jour` | booléen | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen |  |
| `prix_credit` | entier | Prix d'un credit, pour comparer les plans. |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-admin-sources"></a>
#### GET /api/v1/admin/sources/

**Accès : Admin** — chaque source, ses volumes et sa dernière collecte.

Réponse **200** :

Type : liste de [Source](#objet-source)

<a id="get-api-v1-admin-statistiques"></a>
#### GET /api/v1/admin/statistiques/

**Accès : Admin** — compteurs pour un tableau de bord.

Réponse **200** ([Statistiques](#objet-statistiques)) :

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `retenues` | entier |  |
| `ouvertes` | entier |  |
| `actionnables` | entier |  |
| `par_nature` | objet |  |
| `par_secteur` | objet |  |
| `par_source` | objet |  |
| `par_categorie` | objet |  |
| `par_region` | objet |  |
| `suivi` | objet |  |

<a id="get-api-v1-admin-suivi"></a>
#### GET /api/v1/admin/suivi/

**Accès : Admin** — les décisions commerciales, les plus récentes d'abord.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `page` | requête | entier |  |
| `par_page` | requête | entier | 100 au plus. |
| `statut` | requête | `a_etudier` \| `candidature` \| `gagne` \| `hors_sujet` \| `perdu` |  |

Réponse **200** ([PageSuivi](#objet-pagesuivi)) :

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [SuiviLigne](#objet-suiviligne) |  |

<a id="get-api-v1-admin-taches"></a>
#### GET /api/v1/admin/taches/

**Accès : Admin** — tâche en cours, tâches à reprendre, historique, types lançables.

Réponse **200** ([Taches](#objet-taches)) :

| Champ | Type | Note |
|---|---|---|
| `active` | [Tache](#objet-tache) ou null |  |
| `a_reprendre` | liste de [Tache](#objet-tache) |  |
| `automatismes_suspendus` | booléen |  |
| `intervalle_collecte` | entier |  |
| `types` | liste de [TypeTache](#objet-typetache) |  |
| `nb_sources` | entier |  |
| `historique` | liste de [Tache](#objet-tache) |  |

<a id="get-api-v1-admin-taches-tache-id"></a>
#### GET /api/v1/admin/taches/{tache_id}/

**Accès : Admin** — une tâche et son journal (à interroger pendant qu'elle tourne).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `tache_id` | chemin | entier |  |

Réponse **200** ([TacheDetail](#objet-tachedetail)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte |  |
| `libelle` | texte |  |
| `statut` | texte |  |
| `statut_libelle` | texte |  |
| `automatique` | booléen |  |
| `phase` | entier |  |
| `phases` | liste de [Phase](#objet-phase) |  |
| `etape` | texte |  |
| `courant` | entier |  |
| `total` | entier |  |
| `pourcentage` | entier |  |
| `detail` | texte |  |
| `debut` | date-heure |  |
| `fin` | date-heure ou null |  |
| `duree_secondes` | entier |  |
| `journal` | texte |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-taches-tache-id-action"></a>
#### POST /api/v1/admin/taches/{tache_id}/{action}/

**Accès : Admin** — suspendre, annuler ou reprendre une tâche.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `action` | chemin | `annuler` \| `reprendre` \| `suspendre` |  |
| `tache_id` | chemin | entier |  |

Réponse **200** ([TacheReponse](#objet-tachereponse)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `tache` | [Tache](#objet-tache) |  |

Erreurs : 409, 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-taches-lancer-nom"></a>
#### POST /api/v1/admin/taches/lancer/{nom}/

**Accès : Admin** — lance une tâche de fond (une à la fois).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `nom` | chemin | `liens` \| `nuit` \| `tout` \| `trier` \| `veille` |  |

Réponse **200** ([TacheReponse](#objet-tachereponse)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `tache` | [Tache](#objet-tache) |  |

Erreurs : 409, 400, 401, 403, 404, 429.

<a id="post-api-v1-admin-taches-toutes-action"></a>
#### POST /api/v1/admin/taches/toutes/{action}/

**Accès : Admin** — toutes les tâches et les automatismes.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `action` | chemin | `annuler` \| `reprendre` \| `suspendre` |  |

Réponse **200** ([Message](#objet-message)) :

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

Erreurs : 409, 400, 401, 403, 404, 429.

### Utilisateur

<a id="get-api-v1-carte-points"></a>
#### GET /api/v1/carte/points/

**Accès : Connecté** — les offres regroupées par lieu (mêmes filtres que la liste).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `date_a` | requête | date | Échéance jusqu'à. |
| `date_de` | requête | date | Échéance à partir de. |
| `etat` | requête | `actionnables` \| `cloturees` \| `ecartees` \| `retenues` \| `retirees` \| `sans-echeance` \| `toutes` | Onglet (défaut : toutes = ouvertes). |
| `lieu` | requête | texte | Lieu exact, tel que la carte le donne. |
| `nature` | requête | `emploi` \| `inconnue` \| `marche` |  |
| `pays` | requête | texte | Code de /reference/ pays. |
| `q` | requête | texte | Titre, organisation ou catégorie. |
| `region` | requête | `afrique` \| `ameriques` \| `asie-pacifique` \| `europe` \| `inconnue` \| `international` \| `madagascar` \| `moyen-orient` \| `ocean-indien` |  |
| `secteur` | requête | texte | Code de /reference/ secteurs. |

Réponse **200** ([Carte](#objet-carte)) :

| Champ | Type | Note |
|---|---|---|
| `points` | liste de [PointCarte](#objet-pointcarte) | Chaque point porte aussi un compteur par code de secteur. |
| `total` | entier |  |
| `sans_position` | entier |  |

<a id="get-api-v1-moi"></a>
#### GET /api/v1/moi/

**Accès : Connecté** — le compte connecté, son rôle et ses crédits.

Réponse **200** ([Moi](#objet-moi)) :

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `email` | email |  |
| `prenom` | texte |  |
| `nom` | texte |  |
| `admin` | booléen |  |
| `avatar` | texte ou null |  |
| `completion` | entier | Profil rempli, en %. |
| `credits` | [Credits](#objet-credits) |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-notifications"></a>
#### GET /api/v1/notifications/

**Accès : Connecté** — les offres envoyées par email, les plus récentes d'abord.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `page` | requête | entier |  |
| `par_page` | requête | entier | 100 au plus. |

Réponse **200** ([PageNotifications](#objet-pagenotifications)) :

| Champ | Type | Note |
|---|---|---|
| `alertes_actives` | booléen |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Notification](#objet-notification) |  |

<a id="get-api-v1-offres"></a>
#### GET /api/v1/offres/

**Accès : Connecté** — la liste filtrée, échéance la plus proche d'abord.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `date_a` | requête | date | Échéance jusqu'à. |
| `date_de` | requête | date | Échéance à partir de. |
| `etat` | requête | `actionnables` \| `cloturees` \| `ecartees` \| `retenues` \| `retirees` \| `sans-echeance` \| `toutes` | Onglet (défaut : toutes = ouvertes). |
| `lieu` | requête | texte | Lieu exact, tel que la carte le donne. |
| `nature` | requête | `emploi` \| `inconnue` \| `marche` |  |
| `page` | requête | entier |  |
| `par_page` | requête | entier | 100 au plus. |
| `pays` | requête | texte | Code de /reference/ pays. |
| `q` | requête | texte | Titre, organisation ou catégorie. |
| `region` | requête | `afrique` \| `ameriques` \| `asie-pacifique` \| `europe` \| `inconnue` \| `international` \| `madagascar` \| `moyen-orient` \| `ocean-indien` |  |
| `secteur` | requête | texte | Code de /reference/ secteurs. |

Réponse **200** ([PageOffres](#objet-pageoffres)) :

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Offre](#objet-offre) |  |

<a id="get-api-v1-offres-offre-id"></a>
#### GET /api/v1/offres/{offre_id}/

**Accès : Connecté** — la fiche, et les offres voisines de la même source.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `offre_id` | chemin | texte |  |

Réponse **200** ([OffreDetail](#objet-offredetail)) :

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |
| `titre_lisible` | texte |  |
| `organisation` | texte ou null |  |
| `pays` | texte ou null |  |
| `region` | texte |  |
| `region_libelle` | texte |  |
| `source` | texte |  |
| `source_nom` | texte |  |
| `nature` | texte ou null |  |
| `secteur` | texte ou null |  |
| `secteur_libelle` | texte |  |
| `categorie` | texte ou null |  |
| `pertinent` | booléen |  |
| `date_publication` | date ou null |  |
| `date_limite` | date ou null |  |
| `etat_echeance` | `inconnue` \| `presumee` \| `passee` \| `urgente` \| `proche` \| `lointaine` |  |
| `jours` | entier | Jours restants (negatif : passee) ; sans echeance : age de l'offre. |
| `lien_etat` | texte ou null |  |
| `a_un_lien` | booléen |  |
| `lien` | url ou null | Admins seulement. |
| `description` | texte ou null |  |
| `raison` | texte ou null |  |
| `date_ajout` | date-heure |  |
| `lien_verifie_le` | date-heure ou null |  |
| `deja_consultee` | booléen | Ouverte aujourd'hui : la rouvrir est gratuit. |
| `voisines` | liste de [Voisine](#objet-voisine) |  |
| `suivi` | [Suivi](#objet-suivi) ou null | Admins seulement. |

Erreurs : 400, 401, 403, 404, 429.

<a id="post-api-v1-offres-offre-id-consulter"></a>
#### POST /api/v1/offres/{offre_id}/consulter/

**Accès : Connecté** — le lien officiel, contre un crédit (gratuit si déjà ouverte aujourd'hui).

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `offre_id` | chemin | texte |  |

Réponse **200** ([Consulter](#objet-consulter)) :

| Champ | Type | Note |
|---|---|---|
| `lien` | url |  |
| `credits` | [Credits](#objet-credits) |  |

Erreurs : 402 (Plus de crédits : proposer un plan.), 400, 401, 403, 404, 429.

<a id="get-api-v1-plans"></a>
#### GET /api/v1/plans/

**Accès : Public** — les plans d'abonnement proposés.

Réponse **200** :

Type : liste de [Plan](#objet-plan)

<a id="get-api-v1-pour-vous"></a>
#### GET /api/v1/pour-vous/

**Accès : Connecté** — suggestions selon le profil, meilleur score d'abord.

Paramètres :

| Nom | Où | Type | Note |
|---|---|---|---|
| `page` | requête | entier |  |
| `par_page` | requête | entier | 100 au plus. |

Réponse **200** ([PageSuggestions](#objet-pagesuggestions)) :

| Champ | Type | Note |
|---|---|---|
| `profil_vide` | booléen |  |
| `seuil` | entier |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Suggestion](#objet-suggestion) |  |

<a id="get-api-v1-profil"></a>
#### GET /api/v1/profil/

**Accès : Connecté** — toutes les sections du profil.

Réponse **200** ([Profil](#objet-profil)) :

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

<a id="get-api-v1-profil-cv"></a>
#### GET /api/v1/profil/cv/

**Accès : Connecté** — GET\|POST\|DELETE /api/v1/profil/cv/ — télécharger, déposer (multipart « fichier »), supprimer le CV.

Réponse **200** : le fichier (`application/octet-stream`).

<a id="post-api-v1-profil-cv"></a>
#### POST /api/v1/profil/cv/

**Accès : Connecté** — GET\|POST\|DELETE /api/v1/profil/cv/ — télécharger, déposer (multipart « fichier »), supprimer le CV.

Corps (`multipart/form-data`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `fichier` | fichier | oui | PDF ou DOCX, 5 Mo au plus. |

Réponse **201** ([Cv](#objet-cv)) :

| Champ | Type | Note |
|---|---|---|
| `nom` | texte |  |
| `depose_le` | date-heure |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="delete-api-v1-profil-cv"></a>
#### DELETE /api/v1/profil/cv/

**Accès : Connecté** — GET\|POST\|DELETE /api/v1/profil/cv/ — télécharger, déposer (multipart « fichier »), supprimer le CV.

Réponse **204** : vide.

<a id="put-api-v1-profil-domaines"></a>
#### PUT /api/v1/profil/domaines/

**Accès : Connecté** — remplace la section « domaines » (la section complète, au format de GET /profil/).

Corps (`application/json`, `multipart/form-data`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `secteurs` | liste de entier | non | ids de /reference/ (profil.secteurs). |
| `categories` | liste de entier | non |  |
| `competences_texte` | texte | non | Séparées par des virgules, 30 au plus. |
| `mots_cles` | texte | non |  |

Réponse **200** ([Profil](#objet-profil)) :

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="put-api-v1-profil-perso"></a>
#### PUT /api/v1/profil/perso/

**Accès : Connecté** — remplace la section « perso » (la section complète, au format de GET /profil/).

Corps (`application/json`, `multipart/form-data`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `first_name` | texte | non | (max 150 car.) |
| `last_name` | texte | non | (max 150 car.) |
| `telephone` | texte | non |  |
| `adresse` | texte | non |  |
| `ville` | texte | non |  |
| `region` | texte | non |  |
| `code_postal` | texte | non |  |
| `pays` | entier ou null | non | id d'un pays de /reference/ (profil.pays). |
| `date_naissance` | date ou null | non |  |
| `photo` | fichier | non | Multipart : PNG, JPEG ou WebP, 2 Mo. |
| `supprimer_photo` | booléen | non |  |

Réponse **200** ([Profil](#objet-profil)) :

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-profil-photo"></a>
#### GET /api/v1/profil/photo/

**Accès : Connecté** — la photo de profil (image).

Réponse **200** : le fichier (`image/*`).

<a id="put-api-v1-profil-preferences"></a>
#### PUT /api/v1/profil/preferences/

**Accès : Connecté** — remplace la section « preferences » (la section complète, au format de GET /profil/).

Corps (`application/json`, `multipart/form-data`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `pays` | liste de entier | non |  |
| `regions` | liste de `madagascar` \| `ocean-indien` \| `afrique` \| `europe` \| `moyen-orient` \| `asie-pacifique` \| `ameriques` \| `international` | non |  |
| `villes` | texte | non |  |
| `types_offres` | liste de `marche` \| `emploi` | non |  |
| `teletravail` | booléen | non |  |
| `seuil` | entier | non | Score minimal des suggestions. (min 0) |
| `notifications` | booléen | non |  |

Réponse **200** ([Profil](#objet-profil)) :

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="put-api-v1-profil-pro"></a>
#### PUT /api/v1/profil/pro/

**Accès : Connecté** — remplace la section « pro » (la section complète, au format de GET /profil/).

Corps (`application/json`, `multipart/form-data`) :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `titre` | texte | non |  |
| `description` | texte | non |  |
| `annees_experience` | entier ou null | non | (min 0) |
| `niveau_etudes` | `bac` \| `bac2` \| `bac3` \| `bac5` \| `doctorat` \| `autre` | non |  |
| `type_contrat` | `cdi` \| `cdd` \| `consultant` \| `stage` \| `alternance` \| `volontariat` | non |  |
| `disponibilite` | `immediate` \| `1mois` \| `3mois` \| `a_discuter` | non |  |
| `mode_travail` | `site` \| `teletravail` \| `hybride` | non |  |

Réponse **200** ([Profil](#objet-profil)) :

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

Erreurs : 400, 401, 403, 404, 429.

<a id="get-api-v1-reference"></a>
#### GET /api/v1/reference/

**Accès : Public** — les listes de choix (filtres, formulaires du profil).

Réponse **200** ([Reference](#objet-reference)) :

| Champ | Type | Note |
|---|---|---|
| `etats` | liste de [Choix](#objet-choix) | Valeurs de ?etat= (onglets de la liste). |
| `natures` | liste de [Choix](#objet-choix) |  |
| `secteurs` | liste de [Choix](#objet-choix) | Valeurs de ?secteur=. |
| `pays` | liste de [Choix](#objet-choix) | Valeurs de ?pays=. |
| `regions` | liste de [Choix](#objet-choix) | Valeurs de ?region=. |
| `statuts_suivi` | liste de [Choix](#objet-choix) |  |
| `profil` | [ReferenceProfil](#objet-referenceprofil) | Choix du profil, designes par id. |
| `credits_gratuits_par_jour` | entier |  |

## 3. API publique (`/api/public/`)

Aucune connexion, lecture seule, limitée en débit. Ni le lien officiel, ni le suivi
commercial, ni les offres écartées.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/public/` | Index : liste des routes |
| GET | `/api/public/offres/` | Offres ouvertes. Filtres : `q nature secteur source categorie pays region lieu urgence` (jours), `cloturees=1`, `tri` ; pagination `depuis` et `limite`. Réponse `{"total", "depuis", "limite", "tri", "offres"}` |
| GET | `/api/public/offres/{id}/` | Une offre |
| GET | `/api/public/statistiques/` | Chiffres globaux |
| GET | `/api/public/sources/` | Sources collectées |
| GET | `/api/public/secteurs/` | Secteurs |
| GET | `/api/public/regions/` | Régions |
| GET | `/api/public/lieux/` | Lieux connus |
| GET | `/api/public/carte/points/` | Points de la carte |

## 4. API machine (`/api/`)

Pour les scripts et les automatisations, **pas pour les applis**. Elle demande une clé
machine (`X-API-Key: veille_...` ou `Authorization: Bearer veille_...`), créée par un admin
avec `POST /api/v1/admin/cles/`. Une session ou un `X-Session-Token` n'y donnent pas accès.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/offres/` | Liste des offres |
| GET | `/api/offres/{id}/` | Une offre, avec le lien |
| GET | `/api/statistiques/` | Statistiques |
| GET | `/api/sources/` | Sources |
| GET | `/api/secteurs/` | Secteurs |
| GET | `/api/regions/` | Régions |
| GET | `/api/carte/points/` | Points de la carte |
| GET | `/api/suivi/` | Suivi commercial |
| POST | `/api/offres/{id}/decision/` | `{"statut", "note"}` |
| POST | `/api/offres/{id}/echeance/` | `{"echeance": "AAAA-MM-JJ"}` |
| POST | `/api/offres/{id}/verdict/` | `{"pertinent": true\|false}` |

## Objets

Les objets renvoyés par `/api/v1/`, cités dans les réponses ci-dessus.

<a id="objet-abonnement"></a>
### Abonnement

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `plan` | [PlanCourt](#objet-plancourt) |  |
| `statut` | `attente` \| `valide` \| `refuse` |  |
| `statut_libelle` | texte |  |
| `etat` | texte | attente, refuse, actif ou termine. |
| `demande_le` | date-heure |  |
| `debut` | date ou null |  |
| `fin` | date ou null | Dernier jour inclus ; null : sans fin. |
| `credits_jour` | entier |  |
| `credits_restants` | entier |  |

<a id="objet-abonnementadmin"></a>
### AbonnementAdmin

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `plan` | [PlanCourt](#objet-plancourt) |  |
| `statut` | `attente` \| `valide` \| `refuse` |  |
| `statut_libelle` | texte |  |
| `etat` | texte | attente, refuse, actif ou termine. |
| `demande_le` | date-heure |  |
| `debut` | date ou null |  |
| `fin` | date ou null | Dernier jour inclus ; null : sans fin. |
| `credits_jour` | entier |  |
| `credits_restants` | entier |  |
| `utilisateur` | [UtilisateurCourt](#objet-utilisateurcourt) |  |
| `valide_par` | texte ou null |  |

<a id="objet-carte"></a>
### Carte

| Champ | Type | Note |
|---|---|---|
| `points` | liste de [PointCarte](#objet-pointcarte) | Chaque point porte aussi un compteur par code de secteur. |
| `total` | entier |  |
| `sans_position` | entier |  |

<a id="objet-catalogue"></a>
### Catalogue

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `code` | texte |  |
| `nom` | texte |  |
| `actif` | booléen |  |
| `nombre_offres` | entier |  |

<a id="objet-choix"></a>
### Choix

| Champ | Type | Note |
|---|---|---|
| `code` | texte |  |
| `libelle` | texte |  |

<a id="objet-cle"></a>
### Cle

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 80 car.) |
| `active` | booléen |  |
| `cree_le` | date-heure |  |
| `derniere_utilisation` | date-heure ou null |  |
| `revoque_le` | date-heure ou null |  |

<a id="objet-clecreee"></a>
### CleCreee

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `jeton` | texte | Montré une seule fois : seule son empreinte est gardée. |

<a id="objet-consulter"></a>
### Consulter

| Champ | Type | Note |
|---|---|---|
| `lien` | url |  |
| `credits` | [Credits](#objet-credits) |  |

<a id="objet-credits"></a>
### Credits

| Champ | Type | Note |
|---|---|---|
| `illimites` | booléen | Admin : aucune limite, les autres champs sont absents. |
| `du_jour` | entier |  |
| `lots` | entier | Credits de lots d'abonnement en reserve. |
| `total` | entier |  |
| `gratuits_par_jour` | entier |  |

<a id="objet-creditsepuises"></a>
### CreditsEpuises

| Champ | Type | Note |
|---|---|---|
| `erreur` | texte |  |
| `code` | `credits_epuises` |  |
| `credits` | [Credits](#objet-credits) |  |

<a id="objet-cv"></a>
### Cv

| Champ | Type | Note |
|---|---|---|
| `nom` | texte |  |
| `depose_le` | date-heure |  |

<a id="objet-demandecreee"></a>
### DemandeCreee

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `abonnement` | [Abonnement](#objet-abonnement) |  |

<a id="objet-domaines"></a>
### Domaines

Une section du profil. Les champs typent la saisie (schema) ; la regle reste celle du formulaire du site, applique tel quel aux donnees recues.

| Champ | Type | Note |
|---|---|---|
| `secteurs` | liste de entier | ids de /reference/ (profil.secteurs). |
| `categories` | liste de entier |  |
| `competences_texte` | texte | Séparées par des virgules, 30 au plus. |
| `mots_cles` | texte |  |

<a id="objet-emailenregistre"></a>
### EmailEnregistre

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `mot_de_passe_efface` | booléen |  |

<a id="objet-emailtest"></a>
### EmailTest

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `niveau` | `succes` \| `info` |  |

<a id="objet-erreur"></a>
### Erreur

| Champ | Type | Note |
|---|---|---|
| `erreur` | texte |  |
| `champs` | objet | Erreurs par champ, pour une saisie invalide. |

<a id="objet-idnom"></a>
### IdNom

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte |  |

<a id="objet-mesabonnements"></a>
### MesAbonnements

| Champ | Type | Note |
|---|---|---|
| `credits` | [Credits](#objet-credits) |  |
| `abonnements` | liste de [Abonnement](#objet-abonnement) |  |

<a id="objet-message"></a>
### Message

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |

<a id="objet-moi"></a>
### Moi

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `email` | email |  |
| `prenom` | texte |  |
| `nom` | texte |  |
| `admin` | booléen |  |
| `avatar` | texte ou null |  |
| `completion` | entier | Profil rempli, en %. |
| `credits` | [Credits](#objet-credits) |  |

<a id="objet-notification"></a>
### Notification

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `offre` | [OffreCourte](#objet-offrecourte) |  |
| `score` | entier |  |
| `statut` | texte |  |
| `statut_libelle` | texte |  |
| `date` | texte |  |

<a id="objet-offre"></a>
### Offre

Offre annotee par views_web.annoter. Le lien officiel n'est servi qu'aux admins : un utilisateur l'obtient par /offres/<id>/consulter/ (un credit).

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |
| `titre_lisible` | texte |  |
| `organisation` | texte ou null |  |
| `pays` | texte ou null |  |
| `region` | texte |  |
| `region_libelle` | texte |  |
| `source` | texte |  |
| `source_nom` | texte |  |
| `nature` | texte ou null |  |
| `secteur` | texte ou null |  |
| `secteur_libelle` | texte |  |
| `categorie` | texte ou null |  |
| `pertinent` | booléen |  |
| `date_publication` | date ou null |  |
| `date_limite` | date ou null |  |
| `etat_echeance` | `inconnue` \| `presumee` \| `passee` \| `urgente` \| `proche` \| `lointaine` |  |
| `jours` | entier | Jours restants (negatif : passee) ; sans echeance : age de l'offre. |
| `lien_etat` | texte ou null |  |
| `a_un_lien` | booléen |  |
| `lien` | url ou null | Admins seulement. |

<a id="objet-offrecourte"></a>
### OffreCourte

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |

<a id="objet-offredetail"></a>
### OffreDetail

Offre annotee par views_web.annoter. Le lien officiel n'est servi qu'aux admins : un utilisateur l'obtient par /offres/<id>/consulter/ (un credit).

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |
| `titre_lisible` | texte |  |
| `organisation` | texte ou null |  |
| `pays` | texte ou null |  |
| `region` | texte |  |
| `region_libelle` | texte |  |
| `source` | texte |  |
| `source_nom` | texte |  |
| `nature` | texte ou null |  |
| `secteur` | texte ou null |  |
| `secteur_libelle` | texte |  |
| `categorie` | texte ou null |  |
| `pertinent` | booléen |  |
| `date_publication` | date ou null |  |
| `date_limite` | date ou null |  |
| `etat_echeance` | `inconnue` \| `presumee` \| `passee` \| `urgente` \| `proche` \| `lointaine` |  |
| `jours` | entier | Jours restants (negatif : passee) ; sans echeance : age de l'offre. |
| `lien_etat` | texte ou null |  |
| `a_un_lien` | booléen |  |
| `lien` | url ou null | Admins seulement. |
| `description` | texte ou null |  |
| `raison` | texte ou null |  |
| `date_ajout` | date-heure |  |
| `lien_verifie_le` | date-heure ou null |  |
| `deja_consultee` | booléen | Ouverte aujourd'hui : la rouvrir est gratuit. |
| `voisines` | liste de [Voisine](#objet-voisine) |  |
| `suivi` | [Suivi](#objet-suivi) ou null | Admins seulement. |

<a id="objet-pageabonnementsadmin"></a>
### PageAbonnementsAdmin

| Champ | Type | Note |
|---|---|---|
| `en_attente` | entier |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [AbonnementAdmin](#objet-abonnementadmin) |  |

<a id="objet-pagenotifications"></a>
### PageNotifications

| Champ | Type | Note |
|---|---|---|
| `alertes_actives` | booléen |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Notification](#objet-notification) |  |

<a id="objet-pageoffres"></a>
### PageOffres

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Offre](#objet-offre) |  |

<a id="objet-pagesuggestions"></a>
### PageSuggestions

| Champ | Type | Note |
|---|---|---|
| `profil_vide` | booléen |  |
| `seuil` | entier |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [Suggestion](#objet-suggestion) |  |

<a id="objet-pagesuivi"></a>
### PageSuivi

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `page` | entier |  |
| `pages` | entier |  |
| `par_page` | entier |  |
| `resultats` | liste de [SuiviLigne](#objet-suiviligne) |  |

<a id="objet-parametres"></a>
### Parametres

| Champ | Type | Note |
|---|---|---|
| `collecte` | [ParametresCollecte](#objet-parametrescollecte) |  |
| `email` | [ParametresEmail](#objet-parametresemail) |  |
| `pertinence` | liste de [Pertinence](#objet-pertinence) |  |
| `sources` | liste de [SourceParametre](#objet-sourceparametre) |  |

<a id="objet-parametrescollecte"></a>
### ParametresCollecte

| Champ | Type | Note |
|---|---|---|
| `intervalle_collecte` | entier |  |
| `heure_nuit` | texte |  |
| `prochaine` | date-heure |  |
| `automatismes_suspendus` | booléen |  |
| `derniere_auto` | [Tache](#objet-tache) ou null |  |
| `derniere_nuit` | [Tache](#objet-tache) ou null |  |

<a id="objet-parametresemail"></a>
### ParametresEmail

| Champ | Type | Note |
|---|---|---|
| `source` | `ecran` \| `env` \| `console` |  |
| `smtp_hote` | texte |  |
| `smtp_port` | entier |  |
| `smtp_securite` | texte |  |
| `smtp_utilisateur` | texte |  |
| `mot_de_passe_enregistre` | booléen |  |
| `destinataires` | liste de texte |  |
| `securites` | liste de [Choix](#objet-choix) |  |

<a id="objet-perso"></a>
### Perso

Une section du profil. Les champs typent la saisie (schema) ; la regle reste celle du formulaire du site, applique tel quel aux donnees recues.

| Champ | Type | Note |
|---|---|---|
| `first_name` | texte | (max 150 car.) |
| `last_name` | texte | (max 150 car.) |
| `telephone` | texte |  |
| `adresse` | texte |  |
| `ville` | texte |  |
| `region` | texte |  |
| `code_postal` | texte |  |
| `pays` | entier ou null | id d'un pays de /reference/ (profil.pays). |
| `date_naissance` | date ou null |  |

<a id="objet-pertinence"></a>
### Pertinence

| Champ | Type | Note |
|---|---|---|
| `code` | texte |  |
| `libelle` | texte |  |
| `poids` | entier |  |

<a id="objet-phase"></a>
### Phase

| Champ | Type | Note |
|---|---|---|
| `libelle` | texte |  |
| `etat` | `faite` \| `active` \| `a_venir` |  |

<a id="objet-plan"></a>
### Plan

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte | (max 60 car.) |
| `prix` | entier | (min 0) |
| `credits` | entier | (min 1) |
| `par_jour` | booléen | Coché : les crédits s'ajoutent aux 10 gratuits, chaque jour de la période. Décoché : un lot unique, utilisé une fois les crédits du jour épuisés. |
| `duree_jours` | entier ou null | Vide : sans fin (lot utilisable jusqu'à épuisement). (min 0) |
| `actif` | booléen |  |
| `prix_credit` | entier | Prix d'un credit, pour comparer les plans. |

<a id="objet-plancourt"></a>
### PlanCourt

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte |  |
| `prix` | entier |  |

<a id="objet-pointcarte"></a>
### PointCarte

| Champ | Type | Note |
|---|---|---|
| `lieu` | texte |  |
| `lat` | nombre |  |
| `lon` | nombre |  |
| `region` | texte |  |
| `total` | entier |  |
| `marches` | entier |  |
| `emplois` | entier |  |
| `urgentes` | entier |  |
| `exemples` | liste de [OffreCourte](#objet-offrecourte) |  |

<a id="objet-preferences"></a>
### Preferences

Une section du profil. Les champs typent la saisie (schema) ; la regle reste celle du formulaire du site, applique tel quel aux donnees recues.

| Champ | Type | Note |
|---|---|---|
| `pays` | liste de entier |  |
| `regions` | liste de `madagascar` \| `ocean-indien` \| `afrique` \| `europe` \| `moyen-orient` \| `asie-pacifique` \| `ameriques` \| `international` |  |
| `villes` | texte |  |
| `types_offres` | liste de `marche` \| `emploi` |  |
| `teletravail` | booléen |  |
| `seuil` | entier | Score minimal des suggestions. (min 0) |
| `notifications` | booléen |  |

<a id="objet-pro"></a>
### Pro

Une section du profil. Les champs typent la saisie (schema) ; la regle reste celle du formulaire du site, applique tel quel aux donnees recues.

| Champ | Type | Note |
|---|---|---|
| `titre` | texte |  |
| `description` | texte |  |
| `annees_experience` | entier ou null | (min 0) |
| `niveau_etudes` | `bac` \| `bac2` \| `bac3` \| `bac5` \| `doctorat` \| `autre` |  |
| `type_contrat` | `cdi` \| `cdd` \| `consultant` \| `stage` \| `alternance` \| `volontariat` |  |
| `disponibilite` | `immediate` \| `1mois` \| `3mois` \| `a_discuter` |  |
| `mode_travail` | `site` \| `teletravail` \| `hybride` |  |

<a id="objet-profil"></a>
### Profil

Chaque section a les noms de champs de sa saisie : ce que renvoie GET /profil/, on le renvoie modifie a PUT /profil/<section>/.

| Champ | Type | Note |
|---|---|---|
| `perso` | [Perso](#objet-perso) |  |
| `pro` | [Pro](#objet-pro) |  |
| `domaines` | [Domaines](#objet-domaines) |  |
| `preferences` | [Preferences](#objet-preferences) |  |
| `photo` | texte ou null |  |
| `cv` | [Cv](#objet-cv) ou null |  |
| `completion` | entier |  |
| `resume` | liste de [Resume](#objet-resume) |  |

<a id="objet-reference"></a>
### Reference

| Champ | Type | Note |
|---|---|---|
| `etats` | liste de [Choix](#objet-choix) | Valeurs de ?etat= (onglets de la liste). |
| `natures` | liste de [Choix](#objet-choix) |  |
| `secteurs` | liste de [Choix](#objet-choix) | Valeurs de ?secteur=. |
| `pays` | liste de [Choix](#objet-choix) | Valeurs de ?pays=. |
| `regions` | liste de [Choix](#objet-choix) | Valeurs de ?region=. |
| `statuts_suivi` | liste de [Choix](#objet-choix) |  |
| `profil` | [ReferenceProfil](#objet-referenceprofil) | Choix du profil, designes par id. |
| `credits_gratuits_par_jour` | entier |  |

<a id="objet-referenceprofil"></a>
### ReferenceProfil

| Champ | Type | Note |
|---|---|---|
| `secteurs` | liste de [IdNom](#objet-idnom) |  |
| `categories` | liste de [IdNom](#objet-idnom) |  |
| `pays` | liste de [IdNom](#objet-idnom) |  |
| `regions` | liste de [Choix](#objet-choix) |  |
| `types_offres` | liste de [Choix](#objet-choix) |  |
| `niveaux_etudes` | liste de [Choix](#objet-choix) |  |
| `types_contrat` | liste de [Choix](#objet-choix) |  |
| `disponibilites` | liste de [Choix](#objet-choix) |  |
| `modes_travail` | liste de [Choix](#objet-choix) |  |

<a id="objet-resume"></a>
### Resume

| Champ | Type | Note |
|---|---|---|
| `titre` | texte |  |
| `valeurs` | liste de texte |  |

<a id="objet-source"></a>
### Source

| Champ | Type | Note |
|---|---|---|
| `source` | texte |  |
| `total` | entier |  |
| `retenues` | entier |  |
| `actionnables` | entier |  |
| `derniere_collecte` | date-heure |  |

<a id="objet-sourceparametre"></a>
### SourceParametre

| Champ | Type | Note |
|---|---|---|
| `source` | texte |  |
| `nom` | texte |  |
| `site` | texte |  |
| `domaine` | texte |  |
| `total` | entier |  |
| `derniere` | date-heure ou null |  |

<a id="objet-statistiques"></a>
### Statistiques

| Champ | Type | Note |
|---|---|---|
| `total` | entier |  |
| `retenues` | entier |  |
| `ouvertes` | entier |  |
| `actionnables` | entier |  |
| `par_nature` | objet |  |
| `par_secteur` | objet |  |
| `par_source` | objet |  |
| `par_categorie` | objet |  |
| `par_region` | objet |  |
| `suivi` | objet |  |

<a id="objet-suggestion"></a>
### Suggestion

Offre annotee par views_web.annoter. Le lien officiel n'est servi qu'aux admins : un utilisateur l'obtient par /offres/<id>/consulter/ (un credit).

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |
| `titre_lisible` | texte |  |
| `organisation` | texte ou null |  |
| `pays` | texte ou null |  |
| `region` | texte |  |
| `region_libelle` | texte |  |
| `source` | texte |  |
| `source_nom` | texte |  |
| `nature` | texte ou null |  |
| `secteur` | texte ou null |  |
| `secteur_libelle` | texte |  |
| `categorie` | texte ou null |  |
| `pertinent` | booléen |  |
| `date_publication` | date ou null |  |
| `date_limite` | date ou null |  |
| `etat_echeance` | `inconnue` \| `presumee` \| `passee` \| `urgente` \| `proche` \| `lointaine` |  |
| `jours` | entier | Jours restants (negatif : passee) ; sans echeance : age de l'offre. |
| `lien_etat` | texte ou null |  |
| `a_un_lien` | booléen |  |
| `lien` | url ou null | Admins seulement. |
| `score` | entier | Correspondance avec le profil, sur 100. |

<a id="objet-suivi"></a>
### Suivi

| Champ | Type | Note |
|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` |  |
| `statut_libelle` | texte |  |
| `note` | texte |  |
| `echeance` | date ou null |  |
| `echeance_saisie_le` | date-heure ou null |  |
| `decide_par` | texte ou null |  |
| `decide_par_cle` | texte ou null |  |
| `maj_le` | date-heure |  |

<a id="objet-suiviligne"></a>
### SuiviLigne

| Champ | Type | Note |
|---|---|---|
| `statut` | `a_etudier` \| `candidature` \| `gagne` \| `perdu` \| `hors_sujet` |  |
| `statut_libelle` | texte |  |
| `note` | texte |  |
| `echeance` | date ou null |  |
| `echeance_saisie_le` | date-heure ou null |  |
| `decide_par` | texte ou null |  |
| `decide_par_cle` | texte ou null |  |
| `maj_le` | date-heure |  |
| `offre` | [OffreCourte](#objet-offrecourte) |  |

<a id="objet-tache"></a>
### Tache

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte |  |
| `libelle` | texte |  |
| `statut` | texte |  |
| `statut_libelle` | texte |  |
| `automatique` | booléen |  |
| `phase` | entier |  |
| `phases` | liste de [Phase](#objet-phase) |  |
| `etape` | texte |  |
| `courant` | entier |  |
| `total` | entier |  |
| `pourcentage` | entier |  |
| `detail` | texte |  |
| `debut` | date-heure |  |
| `fin` | date-heure ou null |  |
| `duree_secondes` | entier |  |

<a id="objet-tachedetail"></a>
### TacheDetail

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `nom` | texte |  |
| `libelle` | texte |  |
| `statut` | texte |  |
| `statut_libelle` | texte |  |
| `automatique` | booléen |  |
| `phase` | entier |  |
| `phases` | liste de [Phase](#objet-phase) |  |
| `etape` | texte |  |
| `courant` | entier |  |
| `total` | entier |  |
| `pourcentage` | entier |  |
| `detail` | texte |  |
| `debut` | date-heure |  |
| `fin` | date-heure ou null |  |
| `duree_secondes` | entier |  |
| `journal` | texte |  |

<a id="objet-tachereponse"></a>
### TacheReponse

| Champ | Type | Note |
|---|---|---|
| `message` | texte |  |
| `tache` | [Tache](#objet-tache) |  |

<a id="objet-taches"></a>
### Taches

| Champ | Type | Note |
|---|---|---|
| `active` | [Tache](#objet-tache) ou null |  |
| `a_reprendre` | liste de [Tache](#objet-tache) |  |
| `automatismes_suspendus` | booléen |  |
| `intervalle_collecte` | entier |  |
| `types` | liste de [TypeTache](#objet-typetache) |  |
| `nb_sources` | entier |  |
| `historique` | liste de [Tache](#objet-tache) |  |

<a id="objet-typetache"></a>
### TypeTache

| Champ | Type | Note |
|---|---|---|
| `nom` | texte |  |
| `libelle` | texte |  |
| `phases` | liste de texte |  |

<a id="objet-utilisateurcourt"></a>
### UtilisateurCourt

| Champ | Type | Note |
|---|---|---|
| `id` | entier |  |
| `email` | email |  |

<a id="objet-verdict"></a>
### Verdict

| Champ | Type | Note |
|---|---|---|
| `pertinent` | booléen |  |

<a id="objet-voisine"></a>
### Voisine

| Champ | Type | Note |
|---|---|---|
| `id` | texte |  |
| `titre` | texte |  |
| `date_limite` | date ou null |  |

