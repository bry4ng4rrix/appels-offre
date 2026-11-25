# API des frontends (Next.js, Flutter)

Toute l'application est disponible en JSON sous `/api/v1/` (Django REST Framework). La
connexion passe par django-allauth en mode « headless », sous `/_allauth/`.

## Le contrat exact : OpenAPI

| Quoi | Où |
|---|---|
| Schéma de l'API (OpenAPI 3) | `/api/v1/schema/` (YAML ; JSON avec `Accept: application/json`) |
| Documentation interactive | `/api/v1/docs/` |
| Schéma de la connexion (allauth) | `/_allauth/openapi.json`, lisible dans `/_allauth/openapi.html` |

En développement (`DEBUG=True`), le schéma est ouvert à tous. En production, il est
réservé aux admins connectés, car il décrit aussi les routes d'administration.

**Ne codez pas les appels à la main : générez les clients à partir du schéma.** Les types,
les champs obligatoires, les valeurs possibles et les codes d'erreur viennent alors du
serveur lui-même. Relancez la génération à chaque évolution de l'API.

**Next.js (TypeScript)**, avec [openapi-typescript](https://openapi-ts.dev/) et `openapi-fetch` :

```bash
npx openapi-typescript http://localhost:8000/api/v1/schema/ -o src/api/schema.d.ts
```

```ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";

const api = createClient<paths>({ baseUrl: process.env.API_URL });
api.use({ onRequest: ({ request }) => { request.headers.set("X-Session-Token", jeton); } });
const { data, error } = await api.GET("/api/v1/offres/", { params: { query: { etat: "actionnables" } } });
```

**Flutter (Dart)**, avec [openapi-generator](https://openapi-generator.tech/) :

```bash
curl -o schema.yaml http://localhost:8000/api/v1/schema/
npx @openapitools/openapi-generator-cli generate -i schema.yaml -g dart-dio -o packages/label_api
```

Le schéma déclare l'en-tête `X-Session-Token` (`jetonSession`) : les clients générés
l'envoient une fois qu'on leur a donné le jeton.

## Connexion

```http
POST /_allauth/app/v1/auth/login
Content-Type: application/json

{"email": "nom@exemple.org", "password": "..."}
```

La réponse contient `meta.session_token`. Envoyez-le ensuite dans l'en-tête
`X-Session-Token`, à **chaque** appel, sur `/api/v1/` comme sur `/_allauth/`.

| Action | Appel |
|---|---|
| Inscription | `POST /_allauth/app/v1/auth/signup` `{"email", "password"}` (renvoie aussi un jeton) |
| Session en cours | `GET /_allauth/app/v1/auth/session` |
| Déconnexion | `DELETE /_allauth/app/v1/auth/session` |
| Mot de passe oublié, Google | voir `/_allauth/openapi.html` |

Un jeton absent, expiré ou inconnu renvoie **401** (avec l'en-tête `WWW-Authenticate:
X-Session-Token`). Renvoyez alors l'utilisateur vers la connexion.

**Next.js :**
- Côté serveur (route handlers, server components) : utilisez le client `app` et le
  jeton, comme Flutter.
- Dans le navigateur, deux options :
  - le même jeton, à condition d'ajouter l'origine du site à `CORS_ALLOWED_ORIGINS` ;
  - le client `browser` (`/_allauth/browser/v1/...`), qui s'appuie sur le cookie de
    session. Chaque écriture doit alors porter l'en-tête `X-CSRFToken`, lu dans le
    cookie `csrftoken`, sinon elle est refusée avec un **403**.

## Conventions

- **Erreurs** : `{"erreur": "message lisible"}`. Une saisie invalide ajoute
  `"champs": {"nom_du_champ": ["message"]}`, à afficher sous chaque champ.
- **Codes HTTP** :

  | Code | Sens |
  |---|---|
  | 400 | Saisie invalide |
  | 401 | Non connecté |
  | 402 | Crédits épuisés |
  | 403 | Réservé aux admins, ou CSRF manquant |
  | 404 | Introuvable |
  | 409 | Conflit : demande déjà en attente, ou tâche déjà en cours |
  | 429 | Trop d'appels (voir plus bas) |

- **Pagination** : `?page=` et `?par_page=` (100 au plus). Réponse :
  `{"total", "page", "pages", "par_page", "resultats": [...]}`.
- **Dates** au format ISO 8601. **Montants** en ariary, en entiers.
- **Limitation de débit** (réponse 429, réessayer après la durée indiquée par l'en-tête
  `Retry-After`) :

  | Qui ou quoi | Limite par défaut |
  |---|---|
  | Visiteur non connecté | 60 appels/min |
  | Utilisateur connecté | 300 appels/min |
  | Ouvertures d'annonces | 30/min |
  | Dépôts de CV | 20/h |

## Utilisateur

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/v1/reference/` | Listes de choix : états, secteurs, pays, régions, choix du profil (public) |
| GET | `/api/v1/plans/` | Plans d'abonnement proposés (public) |
| GET | `/api/v1/moi/` | Compte, rôle `admin`, crédits restants |
| GET | `/api/v1/offres/` | Liste. Filtres : `etat q secteur pays region lieu nature date_de date_a` |
| GET | `/api/v1/offres/{id}/` | Fiche, offres voisines, `deja_consultee` |
| POST | `/api/v1/offres/{id}/consulter/` | Renvoie le lien officiel contre un crédit ; 402 `credits_epuises` si plus de crédits |
| GET | `/api/v1/carte/points/` | Offres regroupées par lieu (mêmes filtres que la liste) |
| GET | `/api/v1/pour-vous/` | Suggestions avec `score`, critères et complétion du profil |
| GET | `/api/v1/profil/` | Sections `perso`, `pro`, `domaines`, `preferences`, plus le CV et la photo |
| PUT | `/api/v1/profil/{perso,pro,domaines,preferences}/` | Remplace **toute** la section, au format renvoyé par le GET |
| GET, POST, DELETE | `/api/v1/profil/cv/` | Télécharger, déposer (multipart, champ `fichier` ; PDF ou DOCX de 5 Mo au plus), supprimer |
| GET | `/api/v1/profil/photo/` | La photo (image) |
| GET | `/api/v1/notifications/` | Offres envoyées par email |
| GET, POST | `/api/v1/abonnements/` | Mes demandes et mes crédits ; demander un plan avec `{"plan": id}` |

Le lien officiel d'une offre n'apparaît **jamais** dans la liste, ni dans la fiche d'un
utilisateur, ni dans l'API publique. On ne l'obtient que par `consulter`, qui débite un
crédit. Rouvrir la même offre le même jour est gratuit. Les admins voient le champ `lien`
partout.

Pour envoyer la photo de profil, faites un `PUT` multipart sur `/api/v1/profil/perso/` :
mettez le fichier dans le champ `photo`, à côté des autres champs de la section.
`supprimer_photo=true` retire la photo actuelle.

## Admin (`/api/v1/admin/...`, 403 pour un utilisateur simple)

| Domaine | Routes |
|---|---|
| Offres | `POST offres/{id}/decision/` `{"statut", "note"}`, `POST offres/{id}/echeance/` `{"echeance": "AAAA-MM-JJ"}`, `POST offres/{id}/verdict/` `{"pertinent": bool}` |
| Tableaux | `GET statistiques/`, `GET sources/`, `GET suivi/`, `GET exporter/?format=csv\|json` (mêmes filtres que la liste) |
| Abonnements | `GET abonnements/?statut=attente\|valide\|refuse`, `POST abonnements/{id}/valider/`, `POST abonnements/{id}/refuser/` |
| Plans | `GET` ou `POST plans/` (lister, créer), `GET`, `PUT` ou `PATCH plans/{id}/` |
| Tâches | `GET taches/`, `GET taches/{id}/` (avec le journal), `POST taches/lancer/{tout\|veille\|trier\|liens\|nuit}/`, `POST taches/{id}/{suspendre\|annuler\|reprendre}/`, `POST taches/toutes/{suspendre\|annuler\|reprendre}/` |
| Paramètres | `GET parametres/`, `POST parametres/collecte/`, `POST parametres/email/`, `POST parametres/email/tester/`, `POST parametres/pertinence/` |
| Catalogues | `GET` ou `POST {secteurs\|pays}/` (lister, ajouter `{"nom"}`), `PATCH {secteurs\|pays}/{id}/` (renommer), `DELETE {secteurs\|pays}/{id}/` (retirer des choix), `POST {secteurs\|pays}/{id}/basculer/` |
| Clés machine | `GET` ou `POST cles/` (`{"nom"}` ; le jeton n'est renvoyé qu'une fois), `DELETE cles/{id}/` (révoquer) |

Lancer une tâche renvoie **409** si une autre tâche tourne déjà ; c'est alors cette autre
tâche qui est renvoyée. Pendant l'exécution, interrogez `GET taches/{id}/` pour suivre
le `pourcentage`, l'`etape` et le `journal`.

## Configuration du serveur

Dans `.env` (et dans `docker-compose.yml` pour le déploiement) :

```
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.exemple.org
CSRF_TRUSTED_ORIGINS=...          # seulement pour le client « browser » (cookie)
API_DEBIT_ANONYME=60/min          # facultatif
API_DEBIT_UTILISATEUR=300/min     # facultatif
```

Les applis mobiles, ainsi que le rendu côté serveur de Next.js, ne passent pas par CORS.
