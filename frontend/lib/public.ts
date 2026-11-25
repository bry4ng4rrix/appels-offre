import "server-only"

import { cacheLife } from "next/cache"

import { api } from "@/lib/api/serveur"
import type { Choix, EtatEcheance, Offre } from "@/lib/api/types"

// Donnees de l'API publique : les memes pour tous, gardees quelques minutes en cache.

type OffrePublique = {
  id: string
  source: string
  titre: string
  organisation: string | null
  pays: string | null
  localisation: { region: string; region_libelle: string }
  nature: string | null
  secteur: string | null
  categorie: string | null
  date_publication: string | null
  date_limite: string | null
  jours_restants: number | null
  lien_etat: string | null
}

export type Statistiques = { retenues: number; ouvertes: number; urgentes: number; par_nature: Record<string, number> }

function etat(jours: number | null): EtatEcheance {
  if (jours === null) return "inconnue"
  if (jours < 0) return "passee"
  if (jours <= 7) return "urgente"
  return jours <= 21 ? "proche" : "lointaine"
}

/** Une offre publique, mise au format des cartes de l'app (sans lien officiel). */
function versOffre(o: OffrePublique, secteurs: Map<string, string>, sources: Map<string, string>): Offre {
  return {
    id: o.id,
    titre: o.titre,
    titre_lisible: o.titre.replace(/^\[[^\]]+\]\s*/, ""),
    organisation: o.organisation,
    pays: o.pays,
    region: o.localisation.region,
    region_libelle: o.localisation.region_libelle,
    source: o.source,
    source_nom: sources.get(o.source) ?? o.source,
    nature: o.nature,
    secteur: o.secteur,
    secteur_libelle: (o.secteur && secteurs.get(o.secteur)) || "",
    categorie: o.categorie,
    pertinent: true,
    date_publication: o.date_publication,
    date_limite: o.date_limite,
    etat_echeance: etat(o.jours_restants),
    jours: o.jours_restants ?? 0,
    lien_etat: o.lien_etat,
    a_un_lien: true,
  } as Offre
}

export async function vitrine() {
  "use cache"
  cacheLife("minutes")
  const [stats, urgentes, ref, sources] = await Promise.all([
    api<Statistiques>("/api/public/statistiques/", { anonyme: true }),
    api<{ total: number; offres: OffrePublique[] }>("/api/public/offres/", {
      anonyme: true,
      query: { urgence: 7, tri: "echeance", limite: 9 },
    }),
    api<{ secteurs: Choix[] }>("/api/v1/reference/", { anonyme: true }),
    api<{ sources: { source: string; nom?: string }[] }>("/api/public/sources/", { anonyme: true }),
  ])
  const secteurs = new Map(ref.secteurs.map((s) => [s.code, s.libelle]))
  const noms = new Map(sources.sources.map((s) => [s.source, s.nom ?? s.source]))
  return {
    stats,
    nbSources: sources.sources.length,
    urgentes: urgentes.offres.map((o) => versOffre(o, secteurs, noms)),
  }
}

export async function pointsPublics() {
  "use cache"
  cacheLife("minutes")
  return api<{ points: { lieu: string; lat: number; lon: number; total: number; urgentes: number }[] }>(
    "/api/public/carte/points/",
    { anonyme: true },
  ).then((c) => c.points.map(({ lieu, lat, lon, total, urgentes }) => ({ lieu, lat, lon, total, urgentes })))
}
