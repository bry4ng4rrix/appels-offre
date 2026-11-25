import { Suspense } from "react"

import { Panneau } from "@/components/app/coque"
import { EnTetePage, aplatir } from "@/components/app/page"
import { CarteMonde, type Point } from "@/components/carte/carte-monde"
import { FiltresOffres } from "@/components/offres/filtres"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Carte } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, libelle } from "@/lib/i18n"
import { pointsPublics } from "@/lib/public"
import { moiOuRien, reference } from "@/lib/session"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("carte")

const FILTRES = ["etat", "q", "secteur", "pays", "nature", "region", "date_de", "date_a"] as const

export default function PageCarte({ searchParams }: PageProps<"/[lang]/carte">) {
  return (
    <Suspense
      fallback={
        <Panneau>
          <Skeleton className="h-7 w-64" />
          <Skeleton className="mt-6 aspect-[5/2] w-full rounded-[26px]" />
        </Panneau>
      }
    >
      <ContenuCarte searchParams={searchParams} />
    </Suspense>
  )
}

async function ContenuCarte({ searchParams }: Pick<PageProps<"/[lang]/carte">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const [m, d] = await Promise.all([moiOuRien(), dico()])
  const { entier } = formateurs(d.locale)
  const valeurs = Object.fromEntries(FILTRES.map((k) => [k, sp[k]]))
  // Connecte : les filtres de la liste s'appliquent. Visiteur : les points publics.
  const [carte, ref] = await Promise.all([
    m
      ? api<Carte>("/api/v1/carte/points/", { query: valeurs })
      : pointsPublics().then((points) => ({
          points,
          total: points.reduce((s, p) => s + p.total, 0),
          sans_position: 0,
        })),
    reference(),
  ])
  const parametres = new URLSearchParams(Object.entries(valeurs).filter((e): e is [string, string] => !!e[1])).toString()

  return (
    <Panneau>
      <EnTetePage titre={f(d.carteMonde.titre, { n: entier(carte.total), lieux: entier(carte.points.length) })}>
        {d.carteMonde.texte}
        {carte.sans_position > 0 && ` ${f(d.carteMonde.sansPosition, { n: entier(carte.sans_position) })}`}
      </EnTetePage>
      {m && (
        <div className="mt-6">
          <FiltresOffres valeurs={valeurs} secteurs={ref.secteurs} pays={ref.pays} regions={ref.regions.map((r) => ({ ...r, libelle: libelle(d.regions, r.code, r.libelle) }))} caches={["etat"]} />
        </div>
      )}
      <div className="mt-6">
        <CarteMonde points={carte.points as Point[]} connecte={!!m} parametres={parametres} />
      </div>
    </Panneau>
  )
}
