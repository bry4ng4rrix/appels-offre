import { NextResponse, type NextRequest } from "next/server"

import { appel, ErreurApi } from "@/lib/api/serveur"

/** Lectures depuis le navigateur (suivi des taches, fichiers, carte) : GET seulement, vers
 *  /api/v1/ avec le jeton de la session. L'API applique ses propres droits. */
export async function GET(requete: NextRequest, { params }: RouteContext<"/bff/[...chemin]">) {
  const { chemin } = await params
  const cible = `/api/v1/${chemin.map(encodeURIComponent).join("/")}/`
  let r: Response
  try {
    r = await appel(cible + requete.nextUrl.search)
  } catch (e) {
    const statut = e instanceof ErreurApi ? e.statut : 502
    return NextResponse.json({ erreur: "Le serveur ne répond pas." }, { status: statut })
  }
  const entetes = new Headers()
  for (const nom of ["content-type", "content-disposition", "content-length", "retry-after"]) {
    const v = r.headers.get(nom)
    if (v) entetes.set(nom, v)
  }
  entetes.set("cache-control", "private, no-store")
  return new NextResponse(r.body, { status: r.status, headers: entetes })
}
