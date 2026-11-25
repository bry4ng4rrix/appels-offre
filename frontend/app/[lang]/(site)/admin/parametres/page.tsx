import type { Metadata } from "next"
import { Suspense } from "react"

import { Catalogue, FormCollecte, FormEmail, FormPertinence } from "@/components/admin/parametres"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, aplatir } from "@/components/app/page"
import { Onglets } from "@/components/offres/onglets"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { ElementCatalogue, Parametres } from "@/lib/api/types"
import { dateEtHeure, entier } from "@/lib/format"

export const metadata: Metadata = { title: "Paramètres" }

const ONGLETS = [
  { code: "collecte", libelle: "Collecte", texte: "Quand la collecte passe, et la passe de nuit." },
  { code: "email", libelle: "Email", texte: "Le serveur d'envoi des alertes et du récapitulatif." },
  { code: "pertinence", libelle: "Pertinence", texte: "Le poids de chaque critère dans le score des suggestions." },
  { code: "secteurs", libelle: "Secteurs", texte: "Les secteurs proposés dans les filtres et les profils." },
  { code: "pays", libelle: "Pays", texte: "Les pays proposés dans les filtres et les profils." },
  { code: "sources", libelle: "Sources", texte: "Les sites collectés." },
]

export default function PageParametres({ searchParams }: PageProps<"/admin/parametres">) {
  return (
    <Suspense fallback={<Skeleton className="h-[30rem] w-full rounded-[30px]" />}>
      <ContenuParametres searchParams={searchParams} />
    </Suspense>
  )
}

async function ContenuParametres({ searchParams }: Pick<PageProps<"/admin/parametres">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const onglet = ONGLETS.find((o) => o.code === sp.onglet) ?? ONGLETS[0]
  const catalogue = onglet.code === "secteurs" || onglet.code === "pays" ? onglet.code : null
  const [p, elements] = await Promise.all([
    api<Parametres>("/api/v1/admin/parametres/"),
    catalogue ? api<ElementCatalogue[]>(`/api/v1/admin/${catalogue}/`) : Promise.resolve([]),
  ])
  return (
    <>
      <Onglets
        actif={onglet.code}
        onglets={ONGLETS.map((o) => ({ code: o.code, libelle: o.libelle, href: `/admin/parametres?onglet=${o.code}` }))}
      />
      <Panneau className={onglet.code === "collecte" ? "" : ""}>
        <EnTetePage titre={onglet.libelle}>{onglet.texte}</EnTetePage>
        <div className="mt-6">
          {onglet.code === "collecte" && <FormCollecte collecte={p.collecte} />}
          {onglet.code === "email" && <FormEmail email={p.email} />}
          {onglet.code === "pertinence" && <FormPertinence criteres={p.pertinence} />}
          {catalogue && <Catalogue key={catalogue} catalogue={catalogue} elements={elements} />}
          {onglet.code === "sources" && (
            <ul className="divide-y rounded-[22px] verre-carte ">
              {p.sources.map((s) => (
                <li key={s.source} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
                  <span className="min-w-48 flex-1">
                    {s.nom}
                    <a href={s.site} target="_blank" rel="noopener noreferrer" className="ml-2 text-xs text-muted-foreground hover:text-foreground">
                      {s.domaine}
                    </a>
                  </span>
                  <span className="text-muted-foreground tabular-nums">{entier(s.total)} offres</span>
                  <span className="w-44 text-right text-xs text-muted-foreground">{s.derniere ? dateEtHeure(s.derniere) : "jamais collectée"}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Panneau>
    </>
  )
}
