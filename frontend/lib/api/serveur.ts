import "server-only"

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

/** Backend Django. Les appels partent du serveur Next : pas de CORS, le jeton ne touche jamais le navigateur. */
export const API_URL = (process.env.API_URL ?? "http://157.173.103.147:8001").replace(/\/$/, "")
export const COOKIE_JETON = "lc_jeton"

export class ErreurApi extends Error {
  constructor(
    public statut: number,
    message: string,
    public champs?: Record<string, string[]>,
    public corps?: unknown,
  ) {
    super(message)
  }
}

type Methode = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
type Requete = Record<string, string | number | boolean | undefined | null | string[]>

export type Options = {
  methode?: Methode
  corps?: unknown
  query?: Requete
  /** Appel sans jeton (API publique, connexion). */
  anonyme?: boolean
  jeton?: string
}

export async function jetonCourant(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_JETON)?.value
}

export function versQuery(query: Requete = {}): string {
  const p = new URLSearchParams()
  for (const [cle, valeur] of Object.entries(query)) {
    if (valeur === undefined || valeur === null || valeur === "") continue
    for (const v of Array.isArray(valeur) ? valeur : [valeur]) p.append(cle, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ""
}

/** Reponse brute (fichiers). */
export async function appel(chemin: string, o: Options = {}): Promise<Response> {
  const entetes: Record<string, string> = { Accept: "application/json" }
  const jeton = o.anonyme ? undefined : (o.jeton ?? (await jetonCourant()))
  if (jeton) entetes["X-Session-Token"] = jeton
  let corps: BodyInit | undefined
  if (o.corps instanceof FormData) corps = o.corps
  else if (o.corps !== undefined) {
    entetes["Content-Type"] = "application/json"
    corps = JSON.stringify(o.corps)
  }
  try {
    return await fetch(API_URL + chemin + versQuery(o.query), {
      method: o.methode ?? "GET",
      headers: entetes,
      body: corps,
      cache: "no-store",
    })
  } catch {
    throw new ErreurApi(503, "Le serveur ne répond pas. Réessayez dans un instant.")
  }
}

/** Appel JSON. Un jeton refuse renvoie a la connexion ; les autres erreurs deviennent ErreurApi. */
export async function api<T>(chemin: string, o: Options = {}): Promise<T> {
  const r = await appel(chemin, o)
  if (r.status === 401 && !o.anonyme) redirect("/sortie?raison=expiree")
  if (r.status === 204) return undefined as T
  const donnees = await r.json().catch(() => null)
  if (!r.ok) {
    const message =
      donnees?.erreur ?? (r.status === 429 ? "Trop d'appels : réessayez dans une minute." : `Erreur ${r.status}`)
    throw new ErreurApi(r.status, message, donnees?.champs, donnees)
  }
  return donnees as T
}
