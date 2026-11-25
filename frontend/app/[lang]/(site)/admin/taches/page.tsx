import type { Metadata } from "next"
import { Suspense } from "react"

import { Cles, TableauTaches } from "@/components/admin/taches"
import { Panneau } from "@/components/app/coque"
import { EnTetePage } from "@/components/app/page"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Cle, Source, Statistiques, Taches } from "@/lib/api/types"
import { dateEtHeure, entier } from "@/lib/format"

export const metadata: Metadata = { title: "Tâches" }

export default function PageTaches() {
  return (
    <Suspense fallback={<Skeleton className="h-[36rem] w-full rounded-[30px]" />}>
      <ContenuTaches />
    </Suspense>
  )
}

async function ContenuTaches() {
  const [taches, stats, sources, cles] = await Promise.all([
    api<Taches>("/api/v1/admin/taches/"),
    api<Statistiques>("/api/v1/admin/statistiques/"),
    api<Source[]>("/api/v1/admin/sources/"),
    api<Cle[]>("/api/v1/admin/cles/"),
  ])
  const chiffres = [
    { n: stats.total, l: "offres en base" },
    { n: stats.retenues, l: "retenues par le tri" },
    { n: stats.ouvertes, l: "encore ouvertes" },
    { n: stats.actionnables, l: "actionnables" },
  ]
  return (
    <div className="grid gap-4">
      <Panneau>
        <EnTetePage titre="Collecte et tri">
          Lancez une collecte, suivez-la en direct, reprenez une tâche interrompue.
        </EnTetePage>
        <div className="mt-6">
          <TableauTaches initial={taches} />
        </div>
      </Panneau>

      <Panneau>
        <EnTetePage titre="La base en chiffres" />
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {chiffres.map((c) => (
            <div key={c.l} className="rounded-[22px] verre-carte p-5 ">
              <p className="text-4xl font-light tabular-nums">{entier(c.n)}</p>
              <p className="mt-1 text-sm text-muted-foreground">{c.l}</p>
            </div>
          ))}
        </div>
        <h3 className="mt-8 font-medium">Sources ({sources.length})</h3>
        <div className="mt-3 overflow-x-auto rounded-[22px] verre-carte ">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr className="border-b">
                <th className="px-4 py-3 font-normal">Source</th>
                <th className="px-4 py-3 text-right font-normal">Offres</th>
                <th className="px-4 py-3 text-right font-normal">Retenues</th>
                <th className="px-4 py-3 text-right font-normal">Actionnables</th>
                <th className="px-4 py-3 text-right font-normal">Dernière collecte</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sources.map((s) => (
                <tr key={s.source}>
                  <td className="px-4 py-2.5">{s.source}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{entier(s.total)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{entier(s.retenues)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{entier(s.actionnables)}</td>
                  <td className="px-4 py-2.5 text-right text-muted-foreground">{dateEtHeure(s.derniere_collecte)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panneau>

      <Panneau>
        <EnTetePage titre="Clés de l'API machine">
          Pour les scripts qui lisent ou décident sous /api/. Les applis, elles, utilisent la connexion des utilisateurs.
        </EnTetePage>
        <div className="mt-6">
          <Cles cles={cles} />
        </div>
      </Panneau>
    </div>
  )
}
