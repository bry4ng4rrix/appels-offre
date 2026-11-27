import { NextResponse, type NextRequest } from "next/server"

import { COOKIE_LANGUE, LANGUE_DEFAUT, LANGUES, estLangue, type Langue } from "@/lib/i18n/langues"

// Memes noms que dans lib/api/serveur.ts et lib/actions/compte.ts (ce fichier ne peut pas importer "server-only").
const COOKIE_JETON = "lc_jeton"
const COOKIE_APPAREIL = "lc_appareil"
const PUBLIQUES = ["/", "/connexion", "/inscription", "/mot-de-passe-oublie", "/carte"]
const ENTREE = ["/connexion", "/inscription"]
const PREFIXE = new RegExp(`^/(${LANGUES.join("|")})(?=/|$)`)
const UN_AN = 60 * 60 * 24 * 365

/** Langue choisie (cookie), sinon la premiere langue connue du navigateur, sinon le francais. */
function langueDe(requete: NextRequest): Langue {
  const choisie = requete.cookies.get(COOKIE_LANGUE)?.value
  if (estLangue(choisie)) return choisie
  for (const partie of (requete.headers.get("accept-language") ?? "").split(",")) {
    const code = partie.trim().slice(0, 2).toLowerCase()
    if (estLangue(code)) return code
  }
  return LANGUE_DEFAUT
}

/** Les adresses restent sans langue (/offres) : la langue est servie par reecriture vers
 *  /[lang]/offres. Une adresse prefixee (/en/offres) choisit la langue et la retient.
 *  Controle optimiste au passage : sans cookie de session, pas de page privee. */
export function proxy(requete: NextRequest) {
  const { pathname, search } = requete.nextUrl
  const prefixe = pathname.match(PREFIXE)
  const langue = (prefixe?.[1] as Langue | undefined) ?? langueDe(requete)
  const chemin = prefixe ? pathname.slice(prefixe[0].length) || "/" : pathname
  const connecte = requete.cookies.has(COOKIE_JETON)

  let reponse: NextResponse
  if (!connecte && !PUBLIQUES.includes(chemin)) {
    const url = new URL("/connexion", requete.url)
    url.searchParams.set("suivant", chemin + search)
    reponse = NextResponse.redirect(url)
  } else if (connecte && ENTREE.includes(chemin)) {
    reponse = NextResponse.redirect(new URL("/pour-vous", requete.url))
  } else if (prefixe) {
    reponse = NextResponse.next()
  } else {
    reponse = NextResponse.rewrite(new URL(`/${langue}${chemin === "/" ? "" : chemin}${search}`, requete.url))
  }
  // Retenue pour la suite de la navigation, et lue par les Server Actions.
  if (requete.cookies.get(COOKIE_LANGUE)?.value !== langue)
    reponse.cookies.set(COOKIE_LANGUE, langue, { path: "/", maxAge: UN_AN, sameSite: "lax" })
  // Identifiant de cet appareil, envoye a Django a l'inscription : un seul compte par appareil.
  if (!requete.cookies.has(COOKIE_APPAREIL))
    reponse.cookies.set(COOKIE_APPAREIL, crypto.randomUUID(), {
      path: "/",
      maxAge: 2 * UN_AN,
      sameSite: "lax",
      httpOnly: true,
      secure: requete.nextUrl.protocol === "https:",
    })
  return reponse
}

export const config = {
  matcher: ["/((?!_next/|bff/|sortie|favicon|.*\\.(?:svg|png|jpg|ico|webp)$).*)"],
}
