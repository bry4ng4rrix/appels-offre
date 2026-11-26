import { Suspense } from "react"

import { DeciderDemande, DialoguePlan } from "@/components/admin/abonnements"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, Pagination, Vide, aplatir, avecParams } from "@/components/app/page"
import { Statut, tonAbonnement } from "@/components/app/statut"
import { Onglets } from "@/components/offres/onglets"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { PageAbonnementsAdmin, Plan } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, libelle } from "@/lib/i18n"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("abonnements")

const ONGLETS = [
  { code: "attente", cle: "ongletAttente" },
  { code: "valide", cle: "ongletValides" },
  { code: "refuse", cle: "ongletRefuses" },
  { code: "", cle: "ongletHistorique" },
] as const

export default function PageAbonnementsAdminPage({ searchParams }: PageProps<"/[lang]/admin/abonnements">) {
  return (
    <Suspense fallback={<Skeleton className="h-[30rem] w-full rounded-[30px]" />}>
      <Abonnements searchParams={searchParams} />
    </Suspense>
  )
}

async function Abonnements({ searchParams }: Pick<PageProps<"/[lang]/admin/abonnements">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const statut = sp.statut ?? "attente"
  const onglet = statut === "tous" ? "" : statut
  const [p, liste, d] = await Promise.all([
    api<PageAbonnementsAdmin>("/api/v1/admin/abonnements/", { query: { statut, page: sp.page } }),
    api<Plan[]>("/api/v1/admin/plans/"),
    dico(),
  ])
  const { ariary, date, dateEtHeure, entier } = formateurs(d.locale)
  const a = d.adminAbo
  return (
    <div className="grid gap-4">
      <div className="min-w-0">
        <Onglets
          actif={onglet}
          onglets={ONGLETS.map((o) => ({
            libelle: a[o.cle],
            href: avecParams("/admin/abonnements", {}, { statut: o.code === "attente" ? undefined : o.code || "tous" }),
            code: o.code,
            nombre: o.code === "attente" ? p.en_attente : o.code === onglet ? p.total : undefined,
          }))}
        />
        <Panneau className={statut === "attente" ? "" : ""}>
          <EnTetePage titre={statut === "attente" ? f(a.aTraiter, { n: entier(p.en_attente) }) : f(a.demandes, { n: entier(p.total) })}>
            {a.texte}
          </EnTetePage>
          {p.resultats.length === 0 ? (
            <Vide titre={statut === "attente" ? a.aucuneAttente : a.aucune}>
              {a.videTexte}
            </Vide>
          ) : (
            <ul className="mt-6 grid gap-2">
              {p.resultats.map((ab) => (
                <li key={ab.id} className="grid gap-4 rounded-[22px] verre-carte p-4 md:grid-cols-[1.4fr_1fr_1fr_auto] md:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ambre text-sm font-medium text-ambre-foreground">
                      {ab.utilisateur.email.charAt(0).toUpperCase()}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{ab.utilisateur.email}</p>
                      <p className="text-xs text-muted-foreground">{f(a.demandeLe, { date: dateEtHeure(ab.demande_le) })}</p>
                    </div>
                  </div>
                  <div className="text-sm">
                    <p>{ab.plan.nom}</p>
                    <p className="text-xs text-muted-foreground">{ab.debut ? f(d.abonnement.du_au, { debut: date(ab.debut), fin: ab.fin ? date(ab.fin) : d.abonnement.epuisement }) : a.pasActif}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Statut ton={tonAbonnement(ab.etat)}>{libelle(d.abonnement.etats, ab.etat, ab.statut_libelle)}</Statut>
                    {ab.valide_par && <span>{f(a.par, { qui: ab.valide_par })}</span>}
                  </div>
                  {ab.statut === "attente" ? <DeciderDemande id={ab.id} /> : <span className="text-sm text-muted-foreground tabular-nums">{f(a.restants, { n: ab.credits_restants })}</span>}
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
        <EnTetePage titre={a.plans} actions={<DialoguePlan />}>
          {a.plansTexte}
        </EnTetePage>
        <ul className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {liste.map((plan) => (
            <li key={plan.id} className="flex flex-col gap-3 rounded-[22px] verre-carte p-5 ">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{plan.nom}</p>
                <Statut ton={plan.actif ? "succes" : "neutre"}>{plan.actif ? a.propose2 : a.masque}</Statut>
              </div>
              <p className="text-3xl font-light">{ariary(plan.prix)}</p>
              <p className="text-sm text-muted-foreground">
                {plan.par_jour ? f(a.parJourN, { n: plan.credits }) : f(a.lotN, { n: plan.credits })}
                {plan.duree_jours ? f(a.jours, { j: plan.duree_jours }) : a.sansLimite}. {f(a.leCredit, { prix: ariary(plan.prix_credit) })}
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
