import type { Metadata } from "next"
import { cookies } from "next/headers"
import { lang } from "next/root-params"

import { DICOS, type Dico } from "@/lib/i18n"
import { COOKIE_LANGUE, LANGUE_DEFAUT, estLangue, type Langue } from "@/lib/i18n/langues"

/** La langue de la requete : le segment [lang] de l'URL (pose par proxy.ts). */
export async function langue(): Promise<Langue> {
  const l = await lang()
  return estLangue(l) ? l : LANGUE_DEFAUT
}

export async function dico() {
  return DICOS[await langue()]
}

/** Dans une Server Action, le segment [lang] n'est pas lisible : le cookie pose par le proxy l'est. */
export async function dicoAction() {
  const c = (await cookies()).get(COOKIE_LANGUE)?.value
  return DICOS[estLangue(c) ? c : LANGUE_DEFAUT]
}

/** generateMetadata d'une page : son titre d'onglet dans la langue de la page. */
export function titre(cle: keyof Dico["titres"]) {
  return async (): Promise<Metadata> => ({ title: (await dico()).titres[cle] })
}
