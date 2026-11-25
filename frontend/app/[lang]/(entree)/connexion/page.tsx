import { Suspense } from "react"

import { aplatir } from "@/components/app/page"
import { FormulaireConnexion } from "@/components/entree/formulaires"
import { titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("connexion")

export default function PageConnexion({ searchParams }: PageProps<"/[lang]/connexion">) {
  return (
    <Suspense fallback={<FormulaireConnexion />}>
      <Connexion searchParams={searchParams} />
    </Suspense>
  )
}

async function Connexion({ searchParams }: Pick<PageProps<"/[lang]/connexion">, "searchParams">) {
  const sp = aplatir(await searchParams)
  return <FormulaireConnexion suivant={sp.suivant} expiree={!!sp.expiree} />
}
