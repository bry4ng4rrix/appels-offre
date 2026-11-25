import type { EtatEcheance } from "@/lib/api/types"

const jourMoisAn = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
const jourMois = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", timeZone: "UTC" })
const dateHeure = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Indian/Antananarivo",
})
const nombre = new Intl.NumberFormat("fr-FR")

export const date = (iso?: string | null) => (iso ? jourMoisAn.format(new Date(iso)) : "—")
export const dateCourte = (iso?: string | null) => (iso ? jourMois.format(new Date(iso)) : "—")
export const dateEtHeure = (iso?: string | null) => (iso ? dateHeure.format(new Date(iso)) : "—")
export const entier = (n?: number | null) => nombre.format(n ?? 0)
export const ariary = (n: number) => `${nombre.format(n)} Ar`
export const pluriel = (n: number, un: string, plusieurs = `${un}s`) => (n > 1 ? plusieurs : un)

/** Tonalite de l'echelle d'echeance : rouge sous 7 j, orange sous 3 semaines, vert au-dela. */
export type Ton = "urgent" | "proche" | "lointaine" | "neutre"

const TONS: Record<EtatEcheance, Ton> = {
  urgente: "urgent",
  proche: "proche",
  lointaine: "lointaine",
  passee: "neutre",
  presumee: "neutre",
  inconnue: "neutre",
}
export const ton = (etat: EtatEcheance): Ton => TONS[etat]

export const GROUPES: Record<EtatEcheance, string> = {
  urgente: "Clôture sous 7 jours",
  proche: "Clôture dans 8 à 21 jours",
  lointaine: "Clôture dans plus de 3 semaines",
  passee: "Clôturées",
  presumee: "Sans échéance, présumées closes",
  inconnue: "Sans échéance",
}

/** Part de la fenetre de 30 jours deja consumee : la meche des cartes. */
export function consume(jours: number, etat: EtatEcheance): number {
  if (etat === "passee") return 100
  if (etat === "inconnue" || etat === "presumee") return Math.min(100, Math.max(4, (jours / 30) * 100))
  return Math.min(100, Math.max(4, 100 - (jours / 30) * 100))
}

export function nature(code?: string | null) {
  if (code === "emploi") return "Poste"
  if (code === "marche") return "Marché"
  return null
}
