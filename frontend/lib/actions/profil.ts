"use server"

import { api } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"
import { executer } from "@/lib/actions/outils"
import { dicoAction } from "@/lib/i18n/serveur"

const SECTIONS = ["perso", "pro", "domaines", "preferences"] as const
export type Section = (typeof SECTIONS)[number]

/** Remplace une section du profil. Le formulaire part tel quel (multipart) : listes et
 *  fichier compris, validees par les formulaires Django du backend. */
export async function enregistrerSection(section: Section, _: Resultat | null, f: FormData): Promise<Resultat> {
  const d = await dicoAction()
  if (!SECTIONS.includes(section)) return { ok: false, erreur: d.profil.sectionInconnue }
  const photo = f.get("photo")
  if (photo instanceof File && photo.size === 0) f.delete("photo")
  return executer(() => api(`/api/v1/profil/${section}/`, { methode: "PUT", corps: f }), d.profil.enregistre)
}

export async function deposerCv(_: Resultat | null, f: FormData): Promise<Resultat> {
  const d = await dicoAction()
  const fichier = f.get("fichier")
  if (!(fichier instanceof File) || fichier.size === 0) return { ok: false, erreur: d.profil.cvChoisir }
  return executer(() => api("/api/v1/profil/cv/", { methode: "POST", corps: f }), d.profil.cvDepose)
}

export async function supprimerCv() {
  const d = await dicoAction()
  return executer(() => api("/api/v1/profil/cv/", { methode: "DELETE" }), d.profil.cvSupprime)
}
