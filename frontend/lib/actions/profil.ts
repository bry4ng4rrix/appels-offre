"use server"

import { api } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"
import { executer } from "@/lib/actions/outils"

const SECTIONS = ["perso", "pro", "domaines", "preferences"] as const
export type Section = (typeof SECTIONS)[number]

/** Remplace une section du profil. Le formulaire part tel quel (multipart) : listes et
 *  fichier compris, validees par les formulaires Django du backend. */
export async function enregistrerSection(section: Section, _: Resultat | null, f: FormData): Promise<Resultat> {
  if (!SECTIONS.includes(section)) return { ok: false, erreur: "Section inconnue." }
  const photo = f.get("photo")
  if (photo instanceof File && photo.size === 0) f.delete("photo")
  return executer(() => api(`/api/v1/profil/${section}/`, { methode: "PUT", corps: f }), "Profil enregistré.")
}

export async function deposerCv(_: Resultat | null, f: FormData): Promise<Resultat> {
  const fichier = f.get("fichier")
  if (!(fichier instanceof File) || fichier.size === 0) return { ok: false, erreur: "Choisissez un fichier PDF ou DOCX." }
  return executer(() => api("/api/v1/profil/cv/", { methode: "POST", corps: f }), "CV déposé.")
}

export async function supprimerCv() {
  return executer(() => api("/api/v1/profil/cv/", { methode: "DELETE" }), "CV supprimé.")
}
