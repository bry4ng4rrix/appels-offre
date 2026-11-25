import "server-only"

import { refresh } from "next/cache"

import { ErreurApi } from "@/lib/api/serveur"
import type { Resultat } from "@/lib/api/types"
import { dicoAction } from "@/lib/i18n/serveur"

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
    if (e instanceof ErreurApi) {
      const d = await dicoAction()
      // Pannes du transport : message traduit. Les autres viennent de l'API (en francais).
      const erreur = e.statut === 503 ? d.erreurs.serveur : e.statut === 429 ? d.erreurs.tropAppels : e.message
      return { ok: false, erreur, champs: e.champs, statut: e.statut }
    }
    throw e
  }
}

/** Champ de formulaire en texte, sans espaces autour. */
export const texte = (f: FormData, nom: string) => String(f.get(nom) ?? "").trim()
