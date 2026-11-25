"use server"

import { updateTag } from "next/cache"

import { api } from "@/lib/api/serveur"
import type { CleCreee, Resultat, TacheReponse } from "@/lib/api/types"
import { executer, texte } from "@/lib/actions/outils"

const A = "/api/v1/admin"
type Message = { message: string }
type Catalogue = "secteurs" | "pays"

// Abonnements et plans
export async function deciderAbonnement(id: number, action: "valider" | "refuser") {
  return executer(() => api<Message>(`${A}/abonnements/${id}/${action}/`, { methode: "POST" }), (d) => d?.message)
}

export async function enregistrerPlan(id: number | null, _: Resultat | null, f: FormData): Promise<Resultat> {
  const duree = texte(f, "duree_jours")
  const corps = {
    nom: texte(f, "nom"),
    prix: Number(texte(f, "prix") || 0),
    credits: Number(texte(f, "credits") || 0),
    par_jour: f.get("par_jour") === "on",
    duree_jours: duree ? Number(duree) : null,
    actif: f.get("actif") === "on",
  }
  const r = await executer(
    () => api(id ? `${A}/plans/${id}/` : `${A}/plans/`, { methode: id ? "PUT" : "POST", corps }),
    id ? "Plan enregistré." : "Plan créé.",
  )
  if (r.ok) updateTag("plans")
  return r
}

// Taches de fond
export async function lancerTache(nom: string) {
  return executer(() => api<TacheReponse>(`${A}/taches/lancer/${nom}/`, { methode: "POST" }), (d) => d.message)
}

export async function agirSurTache(id: number, action: "suspendre" | "annuler" | "reprendre") {
  return executer(() => api<TacheReponse>(`${A}/taches/${id}/${action}/`, { methode: "POST" }), (d) => d.message)
}

export async function agirSurToutes(action: "suspendre" | "annuler" | "reprendre") {
  return executer(() => api<Message>(`${A}/taches/toutes/${action}/`, { methode: "POST" }), (d) => d?.message)
}

// Parametres
export async function reglerCollecte(_: Resultat | null, f: FormData): Promise<Resultat> {
  const corps = { intervalle_collecte: Number(texte(f, "intervalle_collecte")), heure_nuit: texte(f, "heure_nuit") }
  return executer(() => api<Message>(`${A}/parametres/collecte/`, { methode: "POST", corps }), (d) => d?.message)
}

export async function reglerEmail(_: Resultat | null, f: FormData): Promise<Resultat> {
  const port = texte(f, "smtp_port")
  const corps = {
    smtp_hote: texte(f, "smtp_hote"),
    smtp_port: port ? Number(port) : null,
    smtp_securite: texte(f, "smtp_securite"),
    smtp_utilisateur: texte(f, "smtp_utilisateur"),
    smtp_mot_de_passe: String(f.get("smtp_mot_de_passe") ?? ""),
    destinataires: texte(f, "destinataires").split(/[\s,;]+/).filter(Boolean),
  }
  return executer(() => api<Message>(`${A}/parametres/email/`, { methode: "POST", corps }), (d) => d?.message)
}

export async function testerEmail() {
  return executer(() => api<{ message: string; niveau: string }>(`${A}/parametres/email/tester/`, { methode: "POST" }), (d) => d.message)
}

export async function reglerPertinence(_: Resultat | null, f: FormData): Promise<Resultat> {
  const corps = Object.fromEntries(
    ["competences", "domaine", "categorie", "localisation", "mots_cles"].map((c) => [c, Number(texte(f, c) || 0)]),
  )
  return executer(() => api<Message>(`${A}/parametres/pertinence/`, { methode: "POST", corps }), (d) => d?.message)
}

// Catalogues (secteurs, pays)
export async function ajouterAuCatalogue(catalogue: Catalogue, nom: string) {
  const r = await executer(() => api<Message>(`${A}/${catalogue}/`, { methode: "POST", corps: { nom } }), (d) => d?.message)
  if (r.ok) updateTag("reference")
  return r
}

export async function renommerDansCatalogue(catalogue: Catalogue, id: number, nom: string) {
  const r = await executer(() => api<Message>(`${A}/${catalogue}/${id}/`, { methode: "PATCH", corps: { nom } }), (d) => d?.message)
  if (r.ok) updateTag("reference")
  return r
}

export async function basculerDansCatalogue(catalogue: Catalogue, id: number) {
  const r = await executer(() => api<Message>(`${A}/${catalogue}/${id}/basculer/`, { methode: "POST" }), (d) => d?.message)
  if (r.ok) updateTag("reference")
  return r
}

export async function retirerDuCatalogue(catalogue: Catalogue, id: number) {
  const r = await executer(() => api<Message>(`${A}/${catalogue}/${id}/`, { methode: "DELETE" }), (d) => d?.message ?? "Retiré.")
  if (r.ok) updateTag("reference")
  return r
}

// Cles machine
export async function creerCle(nom: string) {
  return executer(() => api<CleCreee>(`${A}/cles/`, { methode: "POST", corps: { nom } }), (d) => d.message)
}

export async function revoquerCle(id: number) {
  return executer(() => api(`${A}/cles/${id}/`, { methode: "DELETE" }), "Clé révoquée.")
}
