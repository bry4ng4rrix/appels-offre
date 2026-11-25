import type { EtatEcheance } from "@/lib/api/types"

/** Dates et nombres dans la langue de la page (locale : fr-FR, en-GB...). */
export function formateurs(locale: string) {
  const jourMoisAn = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
  const jourMois = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", timeZone: "UTC" })
  const dateHeure = new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Indian/Antananarivo",
  })
  const nombre = new Intl.NumberFormat(locale)
  return {
    date: (iso?: string | null) => (iso ? jourMoisAn.format(new Date(iso)) : "—"),
    dateCourte: (iso?: string | null) => (iso ? jourMois.format(new Date(iso)) : "—"),
    dateEtHeure: (iso?: string | null) => (iso ? dateHeure.format(new Date(iso)) : "—"),
    entier: (n?: number | null) => nombre.format(n ?? 0),
    ariary: (n: number) => `${nombre.format(n)} Ar`,
  }
}

export type Formateurs = ReturnType<typeof formateurs>

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

/** Part de la fenetre de 30 jours deja consumee : la meche des cartes. */
export function consume(jours: number, etat: EtatEcheance): number {
  if (etat === "passee") return 100
  if (etat === "inconnue" || etat === "presumee") return Math.min(100, Math.max(4, (jours / 30) * 100))
  return Math.min(100, Math.max(4, 100 - (jours / 30) * 100))
}
