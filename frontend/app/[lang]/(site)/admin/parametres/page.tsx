import { Suspense } from "react"

import { Catalogue, FormCollecte, FormEmail, FormPertinence } from "@/components/admin/parametres"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, aplatir } from "@/components/app/page"
import { Onglets } from "@/components/offres/onglets"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { ElementCatalogue, Parametres } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f } from "@/lib/i18n"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("parametres")

const ONGLETS = ["collecte", "email", "pertinence", "secteurs", "pays", "sources"] as const

export default function PageParametres({ searchParams }: PageProps<"/[lang]/admin/parametres">) {
  return (
    <Suspense fallback={<Skeleton className="h-[30rem] w-full rounded-[30px]" />}>
      <ContenuParametres searchParams={searchParams} />
    </Suspense>
  )
}

async function ContenuParametres({ searchParams }: Pick<PageProps<"/[lang]/admin/parametres">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const onglet = ONGLETS.find((o) => o === sp.onglet) ?? ONGLETS[0]
  const catalogue = onglet === "secteurs" || onglet === "pays" ? onglet : null
  const [p, elements, d] = await Promise.all([
    api<Parametres>("/api/v1/admin/parametres/"),
    catalogue ? api<ElementCatalogue[]>(`/api/v1/admin/${catalogue}/`) : Promise.resolve([]),
    dico(),
  ])
  const { dateEtHeure, entier } = formateurs(d.locale)
  return (
    <>
      <Onglets
        actif={onglet}
        onglets={ONGLETS.map((o) => ({ code: o, libelle: d.params.onglets[o], href: `/admin/parametres?onglet=${o}` }))}
      />
      <Panneau>
        <EnTetePage titre={d.params.onglets[onglet]}>{d.params.textes[onglet]}</EnTetePage>
        <div className="mt-6">
          {onglet === "collecte" && <FormCollecte collecte={p.collecte} />}
          {onglet === "email" && <FormEmail email={p.email} />}
          {onglet === "pertinence" && <FormPertinence criteres={p.pertinence} />}
          {catalogue && <Catalogue key={catalogue} catalogue={catalogue} elements={elements} />}
          {onglet === "sources" && (
            <ul className="divide-y rounded-[22px] verre-carte ">
              {p.sources.map((s) => (
                <li key={s.source} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
                  <span className="min-w-48 flex-1">
                    {s.nom}
                    <a href={s.site} target="_blank" rel="noopener noreferrer" className="ms-2 text-xs text-muted-foreground hover:text-foreground">
                      {s.domaine}
                    </a>
                  </span>
                  <span className="text-muted-foreground tabular-nums">{f(d.params.nOffres, { n: entier(s.total) })}</span>
                  <span className="w-44 text-end text-xs text-muted-foreground">{s.derniere ? dateEtHeure(s.derniere) : d.params.jamaisCollectee}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Panneau>
    </>
  )
}
