import { cacheLife } from "next/cache"

import { NombreAnime } from "@/components/app/nombre-anime"
import { api } from "@/lib/api/serveur"

type Stats = { ouvertes: number; urgentes: number }

async function statistiques(): Promise<Stats | null> {
  "use cache"
  cacheLife("minutes")
  try {
    return await api<Stats>("/api/public/statistiques/", { anonyme: true })
  } catch {
    return null
  }
}

/** Deux chiffres vivants, lus dans l'API publique (mis en cache quelques minutes). */
export async function ChiffresEntree() {
  const s = await statistiques()
  if (!s) return null
  return (
    <dl className="grid grid-cols-2 gap-3">
      {[
        { n: s.ouvertes, l: "offres ouvertes en ce moment" },
        { n: s.urgentes, l: "ferment dans les 7 jours" },
      ].map(({ n, l }) => (
        <div key={l} className="rounded-[22px] verre-carte p-5 ">
          <dt className="sr-only">{l}</dt>
          <dd>
            <span className="block text-4xl font-light">
              <NombreAnime valeur={n} depuisZero duree={1.4} />
            </span>
            <span className="mt-1 block text-sm text-muted-foreground">{l}</span>
          </dd>
        </div>
      ))}
    </dl>
  )
}
