import "server-only"

import { cacheLife, cacheTag } from "next/cache"
import { cache } from "react"
import { notFound } from "next/navigation"

import { api, jetonCourant } from "@/lib/api/serveur"
import type { Moi, Plan, Reference } from "@/lib/api/types"

/** L'utilisateur courant, lu une fois par requete. */
export const moi = cache(() => api<Moi>("/api/v1/moi/"))

/** null pour un visiteur : les pages publiques s'en servent pour adapter leurs boutons. */
export const moiOuRien = cache(async (): Promise<Moi | null> => {
  if (!(await jetonCourant())) return null
  return moi()
})

export async function exigerAdmin(): Promise<Moi> {
  const m = await moi()
  if (!m.admin) notFound()
  return m
}

// Donnees publiques, les memes pour tous : gardees quelques minutes. Sans ce cache,
// chaque page appellerait l'API en anonyme depuis l'unique adresse du serveur Next,
// et epuiserait vite la limite d'appels anonymes de l'API (60/min par adresse).
// Les actions d'administration les rafraichissent aussitot (updateTag).

export async function reference(): Promise<Reference> {
  "use cache"
  cacheLife("minutes")
  cacheTag("reference")
  return api<Reference>("/api/v1/reference/", { anonyme: true })
}

export async function plans(): Promise<Plan[]> {
  "use cache"
  cacheLife("minutes")
  cacheTag("plans")
  try {
    return await api<Plan[]>("/api/v1/plans/", { anonyme: true })
  } catch {
    // API injoignable (build, panne) : pas de plans affiches, nouvel essai dans la minute.
    return []
  }
}
