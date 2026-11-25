// Types exacts de l'API, generes depuis /api/v1/schema/ : `pnpm api:types`.
import type { components } from "./schema"

type S = components["schemas"]

export type Offre = S["Offre"]
export type OffreDetail = S["OffreDetail"]
export type Suggestion = S["Suggestion"]
export type EtatEcheance = S["EtatEcheanceEnum"]
export type StatutSuivi = S["StatutSuiviEnum"]
export type Suivi = S["Suivi"]
export type Moi = S["Moi"]
export type Credits = S["Credits"]
export type Reference = S["Reference"]
export type Choix = S["Choix"]
export type Plan = S["Plan"]
export type Profil = S["Profil"]
export type Abonnement = S["Abonnement"]
export type MesAbonnements = S["MesAbonnements"]
export type Notification = S["Notification"]
export type PointCarte = S["PointCarte"]
export type Carte = S["Carte"]
export type PageOffres = S["PageOffres"]
export type PageSuggestions = S["PageSuggestions"]
export type PageNotifications = S["PageNotifications"]
export type Consulter = S["Consulter"]
export type CreditsEpuises = S["CreditsEpuises"]

// Administration
export type Tache = S["Tache"]
export type TacheDetail = S["TacheDetail"]
export type Taches = S["Taches"]
export type Parametres = S["Parametres"]
export type Statistiques = S["Statistiques"]
export type Source = S["Source"]
export type ElementCatalogue = S["Catalogue"]
export type Cle = S["Cle"]
export type CleCreee = S["CleCreee"]
export type AbonnementAdmin = S["AbonnementAdmin"]
export type PageAbonnementsAdmin = S["PageAbonnementsAdmin"]
export type TacheReponse = S["TacheReponse"]

/** Ce que renvoie chaque Server Action : un message a afficher, ou l'erreur et ses champs. */
export type Resultat<T = unknown> =
  | { ok: true; message?: string; donnees?: T }
  | { ok: false; erreur: string; champs?: Record<string, string[]>; statut?: number }
