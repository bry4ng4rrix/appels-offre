import "server-only"

import { refresh } from "next/cache"

import { ErreurApi } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"

/** Execute un appel d'ecriture et rafraichit l'ecran (credits, listes). Les erreurs d'API
 *  deviennent un Resultat affichable ; redirect() et les vraies pannes remontent. */
export async function executer<T>(
  appel: () => Promise<T>,
  message?: string | ((donnees: T) => string | undefined),
): Promise<Resultat<T>> {
  try {
    const donnees = await appel()
    refresh()
    const texte = typeof message === "function" ? message(donnees) : message
    return { ok: true, message: texte, donnees }
  } catch (e) {
    if (e instanceof ErreurApi) return { ok: false, erreur: e.message, champs: e.champs, statut: e.statut }
    throw e
  }
}

/** Champ de formulaire en texte, sans espaces autour. */
export const texte = (f: FormData, nom: string) => String(f.get(nom) ?? "").trim()
