"use server"

import { cookies, headers } from "next/headers"
import { redirect } from "next/navigation"

import { API_URL, COOKIE_JETON, ErreurApi, api, jetonCourant } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"
import { executer, texte } from "@/lib/actions/outils"
import type { Dico } from "@/lib/i18n"
import { dicoAction } from "@/lib/i18n/serveur"

const ALLAUTH = `${API_URL}/_allauth/app/v1`
const DUREE_COOKIE = 60 * 60 * 24 * 30

type ReponseAllauth = {
  status: number
  errors?: { message: string; code?: string; param?: string }[]
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
    throw new ErreurApi(503, (await dicoAction()).erreurs.serveur)
  }
}

/** Les erreurs d'allauth ({message, param}) au format des formulaires de l'app. */
function enResultat(d: Dico, r: ReponseAllauth, defaut: string): Resultat {
  const champs: Record<string, string[]> = {}
  let generale: string | undefined
  // Les messages d'allauth sont en francais : ceux dont le code est connu sont traduits.
  const traduits = d.allauth as Record<string, string>
  for (const e of r.errors ?? []) {
    const message = (e.code && traduits[e.code]) || e.message
    if (e.param) (champs[e.param] ??= []).push(message)
    else generale ??= message
  }
  if (r.status === 401 && r.data?.flows?.some((f) => f.id === "verify_email" && f.is_pending))
    generale = d.entree.emailConfirmation
  return { ok: false, erreur: generale ?? (Object.keys(champs).length ? d.entree.verifierChamps : defaut), champs }
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
  const d = await dicoAction()
  const r = await allauth("/auth/login", "POST", { email: texte(f, "email"), password: String(f.get("password") ?? "") })
  if (r.status !== 200 || !r.meta?.session_token) return enResultat(d, r, d.entree.erreurConnexion)
  await ouvrirSession(r.meta.session_token)
  redirect(destination(texte(f, "suivant")))
}

export async function inscription(_: Resultat | null, f: FormData): Promise<Resultat> {
  const d = await dicoAction()
  const motDePasse = String(f.get("password") ?? "")
  if (motDePasse !== String(f.get("password2") ?? ""))
    return { ok: false, erreur: d.mdp.differents, champs: { password2: [d.mdp.differents] } }
  const r = await allauth("/auth/signup", "POST", { email: texte(f, "email"), password: motDePasse })
  if (r.status !== 200 || !r.meta?.session_token) return enResultat(d, r, d.entree.erreurInscription)
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
  const d = await dicoAction()
  const r = await allauth("/auth/password/request", "POST", { email: texte(f, "email") })
  if (r.status !== 200) return enResultat(d, r, d.entree.envoiImpossible)
  return { ok: true, message: d.entree.resetEnvoye }
}

export async function changerMotDePasse(_: Resultat | null, f: FormData): Promise<Resultat> {
  const d = await dicoAction()
  const nouveau = String(f.get("new_password") ?? "")
  if (nouveau !== String(f.get("new_password2") ?? ""))
    return { ok: false, erreur: d.mdp.differents, champs: { new_password2: [d.mdp.differents] } }
  const r = await allauth(
    "/account/password/change",
    "POST",
    { current_password: String(f.get("current_password") ?? ""), new_password: nouveau },
    await jetonCourant(),
  )
  if (r.status !== 200) return enResultat(d, r, d.mdp.refuse)
  return { ok: true, message: d.mdp.change }
}

/** Plan demande depuis la page Abonnement. */
export async function demanderPlan(plan: number) {
  return executer(() => api<{ message: string }>("/api/v1/abonnements/", { methode: "POST", corps: { plan } }), (d) => d.message)
}
