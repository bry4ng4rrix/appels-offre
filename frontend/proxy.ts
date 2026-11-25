import { NextResponse, type NextRequest } from "next/server"

// Meme nom que dans lib/api/serveur.ts (ce fichier ne peut pas importer "server-only").
const COOKIE_JETON = "lc_jeton"
const PUBLIQUES = ["/", "/connexion", "/inscription", "/mot-de-passe-oublie", "/carte", "/sortie"]
const ENTREE = ["/connexion", "/inscription"]

/** Controle optimiste : sans cookie, pas de page privee. L'API reverifie chaque appel. */
export function proxy(requete: NextRequest) {
  const { pathname, search } = requete.nextUrl
  const connecte = requete.cookies.has(COOKIE_JETON)

  if (!connecte && !PUBLIQUES.includes(pathname)) {
    const url = new URL("/connexion", requete.url)
    url.searchParams.set("suivant", pathname + search)
    return NextResponse.redirect(url)
  }
  if (connecte && ENTREE.includes(pathname)) return NextResponse.redirect(new URL("/pour-vous", requete.url))
  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/|bff/|favicon|.*\\.(?:svg|png|jpg|ico|webp)$).*)"],
}
