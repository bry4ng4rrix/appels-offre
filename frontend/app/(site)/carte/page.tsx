import type { Metadata } from "next"
import { Suspense } from "react"

import { Panneau } from "@/components/app/coque"
import { EnTetePage, aplatir } from "@/components/app/page"
import { CarteMonde, type Point } from "@/components/carte/carte-monde"
import { FiltresOffres } from "@/components/offres/filtres"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Carte } from "@/lib/api/types"
import { entier } from "@/lib/format"
import { pointsPublics } from "@/lib/public"
import { moiOuRien, reference } from "@/lib/session"

export const metadata: Metadata = { title: "Carte des offres" }

const FILTRES = ["etat", "q", "secteur", "pays", "nature", "region", "date_de", "date_a"] as const

export default function PageCarte({ searchParams }: PageProps<"/carte">) {
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

async function ContenuCarte({ searchParams }: Pick<PageProps<"/carte">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const m = await moiOuRien()
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
      <EnTetePage titre={`${entier(carte.total)} offres ouvertes dans ${entier(carte.points.length)} lieux`}>
        Chaque point regroupe les offres d&apos;un pays ou d&apos;une ville.
        {carte.sans_position > 0 && ` ${entier(carte.sans_position)} offres sans lieu précis n'y figurent pas.`}
      </EnTetePage>
      {m && (
        <div className="mt-6">
          <FiltresOffres valeurs={valeurs} secteurs={ref.secteurs} pays={ref.pays} regions={ref.regions} caches={["etat"]} />
        </div>
      )}
      <div className="mt-6">
        <CarteMonde points={carte.points as Point[]} connecte={!!m} parametres={parametres} />
      </div>
    </Panneau>
  )
}
