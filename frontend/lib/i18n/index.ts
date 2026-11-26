import ar from "./ar.json"
import de from "./de.json"
import en from "./en.json"
import es from "./es.json"
import fr from "./fr.json"
import hi from "./hi.json"
import it from "./it.json"
import ja from "./ja.json"
import nl from "./nl.json"
import pt from "./pt.json"
import ru from "./ru.json"
import sw from "./sw.json"
import tr from "./tr.json"
import zh from "./zh.json"
import type { Langue } from "./langues"

type Profond<T> = { [K in keyof T]: T[K] extends string ? string : Profond<T[K]> }
type Partiel<T> = { [K in keyof T]?: T[K] extends string ? string : Partiel<T[K]> }

/** La forme de fr.json fait foi : une cle absente de en.json est une erreur de type. */
export type Dico = Profond<typeof fr>

/** Les autres langues completent l'anglais : une cle non traduite s'affiche en anglais. */
function completer<T extends object>(base: T, traduction: Partiel<T>): T {
  const resultat = { ...base } as Record<string, unknown>
  for (const [cle, valeur] of Object.entries(traduction)) {
    const origine = resultat[cle]
    resultat[cle] =
      valeur && typeof valeur === "object" && origine && typeof origine === "object"
        ? completer(origine as object, valeur as Partiel<object>)
        : valeur
  }
  return resultat as T
}

const anglais: Dico = en
const partiels: Record<Exclude<Langue, "fr" | "en">, Partiel<Dico>> = { ar, it, es, de, pt, ru, zh, ja, hi, tr, nl, sw }

export const DICOS = {
  fr,
  en: anglais,
  ...Object.fromEntries(Object.entries(partiels).map(([l, p]) => [l, completer(anglais, p)])),
} as Record<Langue, Dico>

/** « {n} offres » -> « 12 offres ». */
export function f(modele: string, valeurs: Record<string, string | number>) {
  return modele.replace(/\{(\w+)\}/g, (_, cle: string) => String(valeurs[cle] ?? `{${cle}}`))
}

/** Singulier ou pluriel selon les regles de la langue (1 en anglais, 0 et 1 en francais). */
export function pl(d: Dico, n: number, un: string, plusieurs: string) {
  return new Intl.PluralRules(d.locale).select(n) === "one" ? un : plusieurs
}

/** Libelle traduit d'un code venu de l'API (etat, region, statut), sinon celui de l'API. */
export function libelle(table: Record<string, string>, code: string, defaut: string) {
  return table[code] ?? defaut
}
