import { Suspense } from "react"

import { Cles, TableauTaches } from "@/components/admin/taches"
import { Panneau } from "@/components/app/coque"
import { EnTetePage } from "@/components/app/page"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Cle, Source, Statistiques, Taches } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f } from "@/lib/i18n"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("taches")

export default function PageTaches() {
  return (
    <Suspense fallback={<Skeleton className="h-[36rem] w-full rounded-[30px]" />}>
      <ContenuTaches />
    </Suspense>
  )
}

async function ContenuTaches() {
  const [taches, stats, sources, cles, d] = await Promise.all([
    api<Taches>("/api/v1/admin/taches/"),
    api<Statistiques>("/api/v1/admin/statistiques/"),
    api<Source[]>("/api/v1/admin/sources/"),
    api<Cle[]>("/api/v1/admin/cles/"),
    dico(),
  ])
  const { dateEtHeure, entier } = formateurs(d.locale)
  const chiffres = [
    { n: stats.total, l: d.taches.enBase },
    { n: stats.retenues, l: d.taches.retenuesTri },
    { n: stats.ouvertes, l: d.taches.encoreOuvertes },
    { n: stats.actionnables, l: d.taches.actionnables },
  ]
  return (
    <div className="grid gap-4">
      <Panneau>
        <EnTetePage titre={d.taches.collecteTri}>
          {d.taches.collecteTexte}
        </EnTetePage>
        <div className="mt-6">
          <TableauTaches initial={taches} />
        </div>
      </Panneau>

      <Panneau>
        <EnTetePage titre={d.taches.chiffres} />
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {chiffres.map((c) => (
            <div key={c.l} className="rounded-[22px] verre-carte p-5 ">
              <p className="text-4xl font-light tabular-nums">{entier(c.n)}</p>
              <p className="mt-1 text-sm text-muted-foreground">{c.l}</p>
            </div>
          ))}
        </div>
        <h3 className="mt-8 font-medium">{f(d.taches.sources, { n: sources.length })}</h3>
        <div className="mt-3 overflow-x-auto rounded-[22px] verre-carte ">
          <table className="w-full text-sm">
            <thead className="text-start text-xs text-muted-foreground">
              <tr className="border-b">
                <th className="px-4 py-3 font-normal">{d.taches.source}</th>
                <th className="px-4 py-3 text-end font-normal">{d.taches.offres}</th>
                <th className="px-4 py-3 text-end font-normal">{d.taches.retenues}</th>
                <th className="px-4 py-3 text-end font-normal">{d.taches.actionnablesCol}</th>
                <th className="px-4 py-3 text-end font-normal">{d.taches.derniereCollecte}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sources.map((s) => (
                <tr key={s.source}>
                  <td className="px-4 py-2.5">{s.source}</td>
                  <td className="px-4 py-2.5 text-end tabular-nums">{entier(s.total)}</td>
                  <td className="px-4 py-2.5 text-end tabular-nums">{entier(s.retenues)}</td>
                  <td className="px-4 py-2.5 text-end tabular-nums">{entier(s.actionnables)}</td>
                  <td className="px-4 py-2.5 text-end text-muted-foreground">{dateEtHeure(s.derniere_collecte)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panneau>

      <Panneau>
        <EnTetePage titre={d.taches.cles}>
          {d.taches.clesTexte}
        </EnTetePage>
        <div className="mt-6">
          <Cles cles={cles} />
        </div>
      </Panneau>
    </div>
  )
}
