import { PartyPopperIcon } from "lucide-react"
import { Suspense } from "react"

import { Anneau } from "@/components/app/anneau"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, aplatir } from "@/components/app/page"
import { OngletsProfil } from "@/components/profil/formulaires"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Profil } from "@/lib/api/types"
import { moi, reference } from "@/lib/session"
import { f } from "@/lib/i18n"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("profil")

export default function PageProfil({ searchParams }: PageProps<"/[lang]/profil">) {
  return (
    <Suspense
      fallback={
        <>
          <Skeleton className="h-16 w-64" />
          <Skeleton className="mt-8 h-11 w-96 rounded-lg" />
          <Skeleton className="mt-6 h-96 w-full rounded-2xl" />
        </>
      }
    >
      <ContenuProfil searchParams={searchParams} />
    </Suspense>
  )
}

async function ContenuProfil({ searchParams }: Pick<PageProps<"/[lang]/profil">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const [profil, ref, m, d] = await Promise.all([api<Profil>("/api/v1/profil/"), reference(), moi(), dico()])
  return (
    <Panneau>
      <div className="flex items-center justify-between gap-4">
        <EnTetePage titre={d.profil.vosInfos} className="min-w-0">
          {f(d.profil.vosInfosTexte, { email: m.email })}
        </EnTetePage>
        <Anneau valeur={profil.completion} taille={72} libelle={f(d.pourVous.completion, { n: profil.completion })} />
      </div>
      {sp.bienvenue && (
        <Alert className="mt-6 border-primary/30 bg-accent">
          <PartyPopperIcon />
          <AlertTitle>{d.profil.bienvenueTitre}</AlertTitle>
          <AlertDescription>
            {d.profil.bienvenueTexte}
          </AlertDescription>
        </Alert>
      )}
      <OngletsProfil profil={profil} reference={ref} />
    </Panneau>
  )
}
