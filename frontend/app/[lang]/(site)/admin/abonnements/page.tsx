import type { Metadata } from "next"
import { Suspense } from "react"

import { DeciderDemande, DialoguePlan } from "@/components/admin/abonnements"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, Pagination, Vide, aplatir, avecParams } from "@/components/app/page"
import { LIBELLES_ABONNEMENT, Statut, tonAbonnement } from "@/components/app/statut"
import { Onglets } from "@/components/offres/onglets"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { PageAbonnementsAdmin, Plan } from "@/lib/api/types"
import { ariary, date, dateEtHeure, entier } from "@/lib/format"

export const metadata: Metadata = { title: "Abonnements" }

const ONGLETS = [
  { code: "attente", libelle: "En attente" },
  { code: "valide", libelle: "Validés" },
  { code: "refuse", libelle: "Refusés" },
  { code: "", libelle: "Historique" },
]

export default function PageAbonnementsAdminPage({ searchParams }: PageProps<"/admin/abonnements">) {
  return (
    <Suspense fallback={<Skeleton className="h-[30rem] w-full rounded-[30px]" />}>
      <Abonnements searchParams={searchParams} />
    </Suspense>
  )
}

async function Abonnements({ searchParams }: Pick<PageProps<"/admin/abonnements">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const statut = sp.statut ?? "attente"
  const onglet = statut === "tous" ? "" : statut
  const [p, liste] = await Promise.all([
    api<PageAbonnementsAdmin>("/api/v1/admin/abonnements/", { query: { statut, page: sp.page } }),
    api<Plan[]>("/api/v1/admin/plans/"),
  ])
  return (
    <div className="grid gap-4">
      <div>
        <Onglets
          actif={onglet}
          onglets={ONGLETS.map((o) => ({
            ...o,
            href: avecParams("/admin/abonnements", {}, { statut: o.code === "attente" ? undefined : o.code || "tous" }),
            code: o.code,
            nombre: o.code === "attente" ? p.en_attente : o.code === onglet ? p.total : undefined,
          }))}
        />
        <Panneau className={statut === "attente" ? "" : ""}>
          <EnTetePage titre={statut === "attente" ? `${entier(p.en_attente)} demandes à traiter` : `${entier(p.total)} demandes`}>
            Valider une demande active le plan dès aujourd&apos;hui. Vérifiez d&apos;abord que le paiement est arrivé.
          </EnTetePage>
          {p.resultats.length === 0 ? (
            <Vide titre={statut === "attente" ? "Aucune demande en attente." : "Aucune demande ici."}>
              Les nouvelles demandes apparaissent ici dès qu&apos;un utilisateur choisit un plan.
            </Vide>
          ) : (
            <ul className="mt-6 grid gap-2">
              {p.resultats.map((a) => (
                <li key={a.id} className="grid gap-4 rounded-[22px] verre-carte p-4 md:grid-cols-[1.4fr_1fr_1fr_auto] md:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ambre text-sm font-medium text-ambre-foreground">
                      {a.utilisateur.email.charAt(0).toUpperCase()}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{a.utilisateur.email}</p>
                      <p className="text-xs text-muted-foreground">Demandé le {dateEtHeure(a.demande_le)}</p>
                    </div>
                  </div>
                  <div className="text-sm">
                    <p>{a.plan.nom}</p>
                    <p className="text-xs text-muted-foreground">{a.debut ? `${date(a.debut)} au ${a.fin ? date(a.fin) : "épuisement"}` : "Pas encore actif"}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Statut ton={tonAbonnement(a.etat)}>{LIBELLES_ABONNEMENT[a.etat] ?? a.statut_libelle}</Statut>
                    {a.valide_par && <span>par {a.valide_par}</span>}
                  </div>
                  {a.statut === "attente" ? <DeciderDemande id={a.id} /> : <span className="text-sm text-muted-foreground tabular-nums">{a.credits_restants} crédits restants</span>}
                </li>
              ))}
            </ul>
          )}
          <Pagination
            page={p.page}
            pages={p.pages}
            total={p.total}
            parPage={p.par_page}
            href={(n) => avecParams("/admin/abonnements", { statut: statut === "attente" ? undefined : statut }, { page: n })}
          />
        </Panneau>
      </div>

      <Panneau>
        <EnTetePage titre="Plans" actions={<DialoguePlan />}>
          Les plans actifs sont proposés sur la page Abonnement et sur l&apos;accueil.
        </EnTetePage>
        <ul className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {liste.map((plan) => (
            <li key={plan.id} className="flex flex-col gap-3 rounded-[22px] verre-carte p-5 ">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{plan.nom}</p>
                <Statut ton={plan.actif ? "succes" : "neutre"}>{plan.actif ? "Proposé" : "Masqué"}</Statut>
              </div>
              <p className="text-3xl font-light">{ariary(plan.prix)}</p>
              <p className="text-sm text-muted-foreground">
                {plan.par_jour ? `+${plan.credits} crédits par jour` : `${plan.credits} crédits en lot`}
                {plan.duree_jours ? `, ${plan.duree_jours} jours` : ", sans limite"}. {ariary(plan.prix_credit)} le crédit.
              </p>
              <div className="mt-auto">
                <DialoguePlan plan={plan} />
              </div>
            </li>
          ))}
        </ul>
      </Panneau>
    </div>
  )
}
