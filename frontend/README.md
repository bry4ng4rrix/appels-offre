# Label Collectes, frontend Next.js

L'interface de Label Collectes en Next.js 16 et shadcn/ui (Base UI), branchée sur l'API
Django (`/api/v1/`, voir `../docs/endpoint.md`).

## Lancer

```bash
pnpm install
cp .env.example .env.local   # API_URL : le backend Django
pnpm dev                     # http://localhost:3000
```

| Variable | Rôle | Défaut |
|---|---|---|
| `API_URL` | Adresse du backend Django | `http://157.173.103.147:8001` |
| `SITE_URL` | Adresse publique du site (aperçus de liens) | `http://localhost:3000` |

## Comment ça marche

- **Le navigateur ne parle jamais à Django.** Les pages (Server Components) et les
  Server Actions appellent l'API côté serveur. Le jeton de session allauth
  (`X-Session-Token`) vit dans un cookie `httpOnly` (`lc_jeton`) : le JavaScript du
  navigateur ne le voit pas, et il n'y a pas de CORS à régler.
- `lib/api/serveur.ts` : les appels à l'API. Un 401 renvoie à la connexion.
- `lib/actions/` : les écritures (connexion, crédits, profil, administration).
- `app/bff/[...chemin]` : les lectures faites depuis le navigateur (suivi des tâches en
  direct, CV, photo, export). GET seulement, avec le jeton de la session.
- `proxy.ts` : sans cookie, les pages privées renvoient à `/connexion`.
- `lib/api/schema.d.ts` : les types exacts de l'API. Après un changement côté Django,
  avec le backend lancé en local : `pnpm api:types`.

## Pages

| Route | Pour qui |
|---|---|
| `/`, `/carte` | Tout le monde |
| `/connexion`, `/inscription`, `/mot-de-passe-oublie` | Visiteurs |
| `/pour-vous`, `/offres`, `/offres/{id}`, `/profil`, `/notifications`, `/abonnement`, `/compte/mot-de-passe` | Connectés |
| `/admin/taches`, `/admin/abonnements`, `/admin/parametres` | Admins |
