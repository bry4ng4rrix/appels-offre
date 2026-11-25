import { PartyPopperIcon } from "lucide-react"
import type { Metadata } from "next"
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

export const metadata: Metadata = { title: "Mon profil" }

export default function PageProfil({ searchParams }: PageProps<"/profil">) {
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

async function ContenuProfil({ searchParams }: Pick<PageProps<"/profil">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const [profil, ref, m] = await Promise.all([api<Profil>("/api/v1/profil/"), reference(), moi()])
  return (
    <Panneau>
      <EnTetePage titre="Vos informations" actions={<Anneau valeur={profil.completion} taille={72} libelle={`Profil complété à ${profil.completion} %`} />}>
        {m.email}. Plus votre profil est complet, plus vos suggestions sont justes.
      </EnTetePage>
      {sp.bienvenue && (
        <Alert className="mt-6 border-primary/30 bg-accent">
          <PartyPopperIcon />
          <AlertTitle>Bienvenue sur Label Collectes</AlertTitle>
          <AlertDescription>
            Indiquez vos domaines et vos lieux : vos suggestions apparaîtront dans « Pour vous ».
          </AlertDescription>
        </Alert>
      )}
      <OngletsProfil profil={profil} reference={ref} />
    </Panneau>
  )
}
