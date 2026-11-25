"use server"

import { refresh } from "next/cache"

import { ErreurApi, api } from "@/lib/api/serveur"
import type { Consulter, CreditsEpuises, Credits, StatutSuivi } from "@/lib/api/types"
import { executer } from "@/lib/actions/outils"

const chemin = (id: string) => `/api/v1/offres/${id.split("/").map(encodeURIComponent).join("/")}`
const admin = (id: string) => `/api/v1/admin/offres/${id.split("/").map(encodeURIComponent).join("/")}`

export type ResultatConsulter =
  | { ok: true; lien: string; credits: Credits }
  | { ok: false; erreur: string; epuises?: boolean; credits?: Credits }

/** Le lien officiel, contre un credit (gratuit si l'offre a deja ete ouverte aujourd'hui). */
export async function consulter(id: string): Promise<ResultatConsulter> {
  try {
    const r = await api<Consulter>(`${chemin(id)}/consulter/`, { methode: "POST" })
    refresh()
    return { ok: true, lien: r.lien, credits: r.credits }
  } catch (e) {
    if (!(e instanceof ErreurApi)) throw e
    const corps = e.corps as CreditsEpuises | undefined
    return { ok: false, erreur: e.message, epuises: e.statut === 402, credits: corps?.credits }
  }
}

export async function decider(id: string, statut: StatutSuivi, note?: string) {
  return executer(() => api(`${admin(id)}/decision/`, { methode: "POST", corps: { statut, note: note ?? "" } }), "Statut enregistré.")
}

export async function dater(id: string, echeance: string) {
  return executer(() => api(`${admin(id)}/echeance/`, { methode: "POST", corps: { echeance } }), "Échéance enregistrée.")
}

export async function juger(id: string, pertinent: boolean) {
  return executer(
    () => api(`${admin(id)}/verdict/`, { methode: "POST", corps: { pertinent } }),
    pertinent ? "Offre retenue." : "Offre écartée.",
  )
}
