"use server"

import { cookies, headers } from "next/headers"
import { redirect } from "next/navigation"

import { API_URL, COOKIE_JETON, ErreurApi, api, jetonCourant } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"
import { executer, texte } from "@/lib/actions/outils"

const ALLAUTH = `${API_URL}/_allauth/app/v1`
const DUREE_COOKIE = 60 * 60 * 24 * 30

type ReponseAllauth = {
  status: number
  errors?: { message: string; param?: string }[]
  meta?: { session_token?: string; is_authenticated?: boolean }
  data?: { flows?: { id: string; is_pending?: boolean }[] }
}

async function allauth(chemin: string, methode: string, corps?: object, jeton?: string) {
  const entetes: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" }
  if (jeton) entetes["X-Session-Token"] = jeton
  try {
    const r = await fetch(ALLAUTH + chemin, {
      method: methode,
      headers: entetes,
      body: corps ? JSON.stringify(corps) : undefined,
      cache: "no-store",
    })
    return (await r.json().catch(() => ({ status: r.status }))) as ReponseAllauth
  } catch {
    throw new ErreurApi(503, "Le serveur ne répond pas. Réessayez dans un instant.")
  }
}

/** Les erreurs d'allauth ({message, param}) au format des formulaires de l'app. */
function enResultat(r: ReponseAllauth, defaut: string): Resultat {
  const champs: Record<string, string[]> = {}
  let generale: string | undefined
  for (const e of r.errors ?? []) {
    if (e.param) (champs[e.param] ??= []).push(e.message)
    else generale ??= e.message
  }
  if (r.status === 401 && r.data?.flows?.some((f) => f.id === "verify_email" && f.is_pending))
    generale = "Un email de confirmation vient de partir : ouvrez le lien qu'il contient, puis connectez-vous."
  return { ok: false, erreur: generale ?? (Object.keys(champs).length ? "Vérifiez les champs signalés." : defaut), champs }
}

async function ouvrirSession(jeton: string) {
  const https = (await headers()).get("x-forwarded-proto") === "https"
  ;(await cookies()).set(COOKIE_JETON, jeton, {
    httpOnly: true,
    sameSite: "lax",
    secure: https,
    path: "/",
    maxAge: DUREE_COOKIE,
  })
}

/** Seules les adresses internes sont suivies apres connexion (pas de redirection ouverte). */
function destination(suivant: string) {
  return suivant.startsWith("/") && !suivant.startsWith("//") ? suivant : "/pour-vous"
}

export async function connexion(_: Resultat | null, f: FormData): Promise<Resultat> {
  const r = await allauth("/auth/login", "POST", { email: texte(f, "email"), password: String(f.get("password") ?? "") })
  if (r.status !== 200 || !r.meta?.session_token) return enResultat(r, "Email ou mot de passe incorrect.")
  await ouvrirSession(r.meta.session_token)
  redirect(destination(texte(f, "suivant")))
}

export async function inscription(_: Resultat | null, f: FormData): Promise<Resultat> {
  const motDePasse = String(f.get("password") ?? "")
  if (motDePasse !== String(f.get("password2") ?? ""))
    return { ok: false, erreur: "Les deux mots de passe diffèrent.", champs: { password2: ["Les deux mots de passe diffèrent."] } }
  const r = await allauth("/auth/signup", "POST", { email: texte(f, "email"), password: motDePasse })
  if (r.status !== 200 || !r.meta?.session_token) return enResultat(r, "Inscription impossible pour le moment.")
  await ouvrirSession(r.meta.session_token)
  redirect("/profil?bienvenue=1")
}

export async function deconnexion() {
  const jeton = await jetonCourant()
  if (jeton) await allauth("/auth/session", "DELETE", undefined, jeton).catch(() => null)
  ;(await cookies()).delete(COOKIE_JETON)
  redirect("/")
}

export async function motDePasseOublie(_: Resultat | null, f: FormData): Promise<Resultat> {
  const r = await allauth("/auth/password/request", "POST", { email: texte(f, "email") })
  if (r.status !== 200) return enResultat(r, "Envoi impossible pour le moment.")
  return { ok: true, message: "Si un compte existe pour cette adresse, un email de réinitialisation vient de partir." }
}

export async function changerMotDePasse(_: Resultat | null, f: FormData): Promise<Resultat> {
  const nouveau = String(f.get("new_password") ?? "")
  if (nouveau !== String(f.get("new_password2") ?? ""))
    return { ok: false, erreur: "Les deux mots de passe diffèrent.", champs: { new_password2: ["Les deux mots de passe diffèrent."] } }
  const r = await allauth(
    "/account/password/change",
    "POST",
    { current_password: String(f.get("current_password") ?? ""), new_password: nouveau },
    await jetonCourant(),
  )
  if (r.status !== 200) return enResultat(r, "Changement refusé.")
  return { ok: true, message: "Mot de passe changé." }
}

/** Plan demande depuis la page Abonnement. */
export async function demanderPlan(plan: number) {
  return executer(() => api<{ message: string }>("/api/v1/abonnements/", { methode: "POST", corps: { plan } }), (d) => d.message)
}
