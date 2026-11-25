import type { Metadata } from "next"
import { Suspense } from "react"

import { CartePlan } from "@/components/abonnement/carte-plan"
import { DemanderPlan } from "@/components/abonnement/demander"
import { Panneau } from "@/components/app/coque"
import { NombreAnime } from "@/components/app/nombre-anime"
import { EnTetePage } from "@/components/app/page"
import { LIBELLES_ABONNEMENT, Statut, tonAbonnement } from "@/components/app/statut"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api } from "@/lib/api/serveur"
import type { MesAbonnements } from "@/lib/api/types"
import { date, dateEtHeure } from "@/lib/format"
import { plans } from "@/lib/session"

export const metadata: Metadata = { title: "Abonnement" }

export default function PageAbonnement() {
  return (
    <Suspense fallback={<Skeleton className="h-[40rem] w-full rounded-2xl" />}>
      <Abonnement />
    </Suspense>
  )
}

function Compteur({ valeur, libelle }: { valeur: number; libelle: string }) {
  return (
    <div className="rounded-[22px] verre-carte p-5">
      <p className="font-chiffres text-5xl leading-none font-light">
        <NombreAnime valeur={valeur} depuisZero />
      </p>
      <p className="mt-2 text-sm text-muted-foreground">{libelle}</p>
    </div>
  )
}

async function Abonnement() {
  const [mes, liste] = await Promise.all([api<MesAbonnements>("/api/v1/abonnements/"), plans()])
  const c = mes.credits
  const gratuits = c.gratuits_par_jour ?? 10

  return (
    <Panneau>
      <EnTetePage titre="Vos crédits">
        Chaque jour, {gratuits} annonces officielles gratuites. Chercher, filtrer et lire les fiches ne coûte rien.
      </EnTetePage>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Compteur valeur={c.du_jour ?? 0} libelle={`crédits du jour, sur ${gratuits}`} />
        <Compteur valeur={c.lots ?? 0} libelle="crédits en réserve (abonnements)" />
        <Compteur valeur={c.total ?? 0} libelle="annonces que vous pouvez encore ouvrir aujourd'hui" />
      </div>

      <section className="mt-16" aria-labelledby="t-plans">
        <h2 id="t-plans" className="text-xl font-medium sm:text-[1.4rem]">
          Choisissez votre plan
        </h2>
        <p className="mt-2 text-muted-foreground">Les crédits s&apos;ajoutent à vos {gratuits} crédits gratuits du jour.</p>
        {liste.length ? (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {liste.map((p, i) => (
              <CartePlan key={p.id} plan={p} gratuits={gratuits} vedette={i === 1} action={<DemanderPlan plan={p.id} vedette={i === 1} />} />
            ))}
          </div>
        ) : (
          <p className="mt-6 text-muted-foreground">Aucun plan proposé pour le moment.</p>
        )}
        <p className="mt-6 max-w-2xl text-sm text-muted-foreground">
          Pas de paiement en ligne : après votre demande, réglez le montant à Label Technology (
          <a className="font-medium text-primary underline-offset-4 hover:underline" href="mailto:contact@labeltechnology.mg">
            contact@labeltechnology.mg
          </a>
          ). Les crédits sont activés dès que le paiement est validé.
        </p>
      </section>

      {mes.abonnements.length > 0 && (
        <section className="mt-16" aria-labelledby="t-demandes">
          <h2 id="t-demandes" className="text-xl font-medium">
            Mes demandes
          </h2>
          <div className="mt-4 overflow-hidden rounded-[22px] verre-carte ">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-5">Plan</TableHead>
                  <TableHead>État</TableHead>
                  <TableHead>Période</TableHead>
                  <TableHead>Crédits restants</TableHead>
                  <TableHead className="pr-5">Demandée le</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mes.abonnements.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="pl-5 font-medium">{a.plan.nom}</TableCell>
                    <TableCell>
                      <Statut ton={tonAbonnement(a.etat)}>{LIBELLES_ABONNEMENT[a.etat] ?? a.statut_libelle}</Statut>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {a.debut ? `${date(a.debut)} au ${a.fin ? date(a.fin) : "épuisement"}` : "—"}
                    </TableCell>
                    <TableCell className="tabular-nums">{a.credits_restants}</TableCell>
                    <TableCell className="pr-5 text-muted-foreground">{dateEtHeure(a.demande_le)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      )}
    </Panneau>
  )
}
