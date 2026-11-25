import type { Metadata } from "next"
import { Suspense } from "react"

import { aplatir } from "@/components/app/page"
import { FormulaireConnexion } from "@/components/entree/formulaires"

export const metadata: Metadata = { title: "Se connecter" }

export default function PageConnexion({ searchParams }: PageProps<"/connexion">) {
  return (
    <Suspense fallback={<FormulaireConnexion />}>
      <Connexion searchParams={searchParams} />
    </Suspense>
  )
}

async function Connexion({ searchParams }: Pick<PageProps<"/connexion">, "searchParams">) {
  const sp = aplatir(await searchParams)
  return <FormulaireConnexion suivant={sp.suivant} expiree={!!sp.expiree} />
}
