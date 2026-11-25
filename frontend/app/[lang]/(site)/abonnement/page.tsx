import { Suspense } from "react"

import { CartePlan } from "@/components/abonnement/carte-plan"
import { DemanderPlan } from "@/components/abonnement/demander"
import { Panneau } from "@/components/app/coque"
import { NombreAnime } from "@/components/app/nombre-anime"
import { EnTetePage } from "@/components/app/page"
import { Statut, tonAbonnement } from "@/components/app/statut"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api } from "@/lib/api/serveur"
import type { MesAbonnements } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, libelle } from "@/lib/i18n"
import { plans } from "@/lib/session"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("abonnement")

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
  const [mes, liste, d] = await Promise.all([api<MesAbonnements>("/api/v1/abonnements/"), plans(), dico()])
  const { date, dateEtHeure } = formateurs(d.locale)
  const c = mes.credits
  const gratuits = c.gratuits_par_jour ?? 10

  return (
    <Panneau>
      <EnTetePage titre={d.abonnement.vosCredits}>
        {f(d.abonnement.intro, { n: gratuits })}
      </EnTetePage>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Compteur valeur={c.du_jour ?? 0} libelle={f(d.abonnement.duJour, { n: gratuits })} />
        <Compteur valeur={c.lots ?? 0} libelle={d.abonnement.reserve} />
        <Compteur valeur={c.total ?? 0} libelle={d.abonnement.restantes} />
      </div>

      <section className="mt-16" aria-labelledby="t-plans">
        <h2 id="t-plans" className="text-xl font-medium sm:text-[1.4rem]">
          {d.abonnement.choisir}
        </h2>
        <p className="mt-2 text-muted-foreground">{f(d.abonnement.ajoutent, { n: gratuits })}</p>
        {liste.length ? (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {liste.map((p, i) => (
              <CartePlan key={p.id} plan={p} gratuits={gratuits} vedette={i === 1} action={<DemanderPlan plan={p.id} vedette={i === 1} />} />
            ))}
          </div>
        ) : (
          <p className="mt-6 text-muted-foreground">{d.abonnement.aucunPlan}</p>
        )}
        <p className="mt-6 max-w-2xl text-sm text-muted-foreground">
          {d.abonnement.paiementAvant}{" "}
          <a className="font-medium text-primary underline-offset-4 hover:underline" href="mailto:contact@labeltechnology.mg">
            contact@labeltechnology.mg
          </a>
          {" "}{d.abonnement.paiementApres}
        </p>
      </section>

      {mes.abonnements.length > 0 && (
        <section className="mt-16" aria-labelledby="t-demandes">
          <h2 id="t-demandes" className="text-xl font-medium">
            {d.abonnement.mesDemandes}
          </h2>
          <div className="mt-4 overflow-hidden rounded-[22px] verre-carte ">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="ps-5">{d.abonnement.plan}</TableHead>
                  <TableHead>{d.abonnement.etat}</TableHead>
                  <TableHead>{d.abonnement.periode}</TableHead>
                  <TableHead>{d.abonnement.creditsRestants}</TableHead>
                  <TableHead className="pe-5">{d.abonnement.demandeeLe}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mes.abonnements.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="ps-5 font-medium">{a.plan.nom}</TableCell>
                    <TableCell>
                      <Statut ton={tonAbonnement(a.etat)}>{libelle(d.abonnement.etats, a.etat, a.statut_libelle)}</Statut>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {a.debut ? f(d.abonnement.du_au, { debut: date(a.debut), fin: a.fin ? date(a.fin) : d.abonnement.epuisement }) : "—"}
                    </TableCell>
                    <TableCell className="tabular-nums">{a.credits_restants}</TableCell>
                    <TableCell className="pe-5 text-muted-foreground">{dateEtHeure(a.demande_le)}</TableCell>
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
