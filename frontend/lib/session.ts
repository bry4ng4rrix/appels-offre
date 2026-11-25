import "server-only"

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

export const reference = cache(() => api<Reference>("/api/v1/reference/", { anonyme: true }))
export const plans = cache(() => api<Plan[]>("/api/v1/plans/", { anonyme: true }))
