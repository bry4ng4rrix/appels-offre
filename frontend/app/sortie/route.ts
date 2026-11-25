import { cookies } from "next/headers"
import { NextResponse, type NextRequest } from "next/server"

import { COOKIE_JETON } from "@/lib/api/serveur"

/** Jeton expire ou revoque : on l'efface (impossible pendant le rendu d'une page), puis connexion. */
export async function GET(requete: NextRequest) {
  ;(await cookies()).delete(COOKIE_JETON)
  return NextResponse.redirect(new URL("/connexion?expiree=1", requete.url))
}
