import { BellOffIcon } from "lucide-react"
import type { Metadata } from "next"
import Link from "next/link"
import { Suspense } from "react"

import { BoutonLien } from "@/components/app/bouton-lien"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, Pagination, Vide, aplatir } from "@/components/app/page"
import { Statut } from "@/components/app/statut"
import { lienOffre } from "@/components/offres/carte-offre"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { PageNotifications } from "@/lib/api/types"
import { dateEtHeure } from "@/lib/format"

export const metadata: Metadata = { title: "Mes notifications" }

export default function PageNotifs({ searchParams }: PageProps<"/notifications">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-2xl" />}>
      <Notifications searchParams={searchParams} />
    </Suspense>
  )
}

async function Notifications({ searchParams }: Pick<PageProps<"/notifications">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const p = await api<PageNotifications>("/api/v1/notifications/", { query: { page: sp.page } })
  return (
    <Panneau>
      <EnTetePage
        titre="Mes notifications"
        actions={
          <BoutonLien href="/profil?onglet=preferences" variant="outline" size="lg">
            Régler mes alertes
          </BoutonLien>
        }
      >
        Les offres envoyées par email après chaque passage de la collecte, toutes les 6 heures.
        {!p.alertes_actives && (
          <span className="mt-3 flex items-center gap-2 font-medium text-proche">
            <BellOffIcon className="size-4" /> Vos alertes sont coupées.
          </span>
        )}
      </EnTetePage>

      {p.resultats.length === 0 ? (
        <Vide titre="Aucune notification pour l'instant.">
          Les prochaines nouvelles offres qui vous correspondent arriveront ici et par email.
        </Vide>
      ) : (
        <ol className="mt-8 divide-y rounded-[22px] bg-card ring-1 ring-border/70">
          {p.resultats.map((n) => (
            <li key={n.id} className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4">
              <span className="font-chiffres w-14 text-2xl font-light text-marque">{n.score}%</span>
              <Link href={lienOffre(n.offre.id)} className="min-w-0 flex-1 text-sm font-medium hover:text-primary">
                <span className="line-clamp-2">{n.offre.titre}</span>
              </Link>
              <Statut ton={n.statut === "sent" ? "succes" : n.statut === "failed" ? "erreur" : "attente"}>{n.statut_libelle}</Statut>
              <span className="w-40 text-right text-xs text-muted-foreground">{dateEtHeure(n.date)}</span>
            </li>
          ))}
        </ol>
      )}
      <Pagination page={p.page} pages={p.pages} total={p.total} parPage={p.par_page} href={(n) => `/notifications?page=${n}`} />
    </Panneau>
  )
}
