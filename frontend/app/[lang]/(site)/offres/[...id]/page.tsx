import { ArrowLeftIcon, CalendarClockIcon, TriangleAlertIcon } from "lucide-react"
import Link from "next/link"
import { notFound } from "next/navigation"
import { Suspense } from "react"

import { Panneau } from "@/components/app/coque"
import { CopierLien, ModifierEcheance } from "@/components/offres/actions-admin"
import { lienOffre } from "@/lib/liens"
import { Consulter } from "@/components/offres/consulter"
import { CompteARebours, Meche, texteEcheance } from "@/components/offres/echeance"
import { IconeSecteur } from "@/components/offres/icone-secteur"
import { SuiviAdmin, Verdict } from "@/components/offres/suivi-admin"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ErreurApi, api } from "@/lib/api/serveur"
import type { OffreDetail, Suivi } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, libelle } from "@/lib/i18n"
import { moi, reference } from "@/lib/session"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("fiche")


export default function PageOffre({ params }: PageProps<"/[lang]/offres/[...id]">) {
  return (
    <Suspense fallback={<Chargement />}>
      <Fiche params={params} />
    </Suspense>
  )
}

function Chargement() {
  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_22rem]">
      <div className="grid content-start gap-4">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-6 w-72 rounded-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
      <Skeleton className="h-96 rounded-2xl" />
    </div>
  )
}

function Puce({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full verre-carte px-3 py-1 text-xs ">{children}</span>
  )
}

async function Fiche({ params }: Pick<PageProps<"/[lang]/offres/[...id]">, "params">) {
  const { id: segments } = await params
  // Selon la version, Next rend les segments encodes ou non : on decode prudemment.
  const id = segments.map((s) => { try { return decodeURIComponent(s) } catch { return s } }).join("/")
  const [offre, m, ref, d] = await Promise.all([
    api<OffreDetail>(`/api/v1/offres/${id.split("/").map(encodeURIComponent).join("/")}/`).catch((e) => {
      if (e instanceof ErreurApi && e.statut === 404) notFound()
      throw e
    }),
    moi(),
    reference(),
    dico(),
  ])
  const { date, dateCourte } = formateurs(d.locale)
  const etatLien = offre.lien_etat ? (d.fiche.etatsLien as Record<string, string>)[offre.lien_etat] : undefined
  const suivi = (offre.suivi ?? null) as Suivi | null
  const ouverte = ["urgente", "proche", "lointaine"].includes(offre.etat_echeance)

  return (
    <Panneau>
      <Link href="/offres" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4 rtl:rotate-180" /> {d.commun.retourOffres}
      </Link>

      <div className="mt-6 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2">
            {offre.secteur && (
              <Puce>
                <IconeSecteur code={offre.secteur} className="size-3.5" />
                {offre.secteur_libelle}
              </Puce>
            )}
            {(offre.nature === "emploi" || offre.nature === "marche") && <Puce>{offre.nature === "emploi" ? d.nature.emploiLong : d.nature.marche}</Puce>}
            <Puce>{libelle(d.regions, offre.region, offre.region_libelle)}</Puce>
            <Puce>{offre.source_nom}</Puce>
            {m.admin && <Puce>{offre.pertinent ? d.fiche.retenue : d.fiche.ecartee}</Puce>}
          </div>
          <h2 className="mt-5 text-3xl leading-tight font-normal tracking-tight text-balance sm:text-[2.4rem]">
            {offre.titre_lisible}
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {offre.organisation || d.fiche.organisationInconnue}
            {offre.pays ? `, ${offre.pays}` : ""}
          </p>

          {etatLien && (
            <Alert className="mt-6 border-proche/40 bg-proche/5">
              <TriangleAlertIcon className="text-proche" />
              <AlertTitle>{etatLien}</AlertTitle>
              <AlertDescription>
                {f(d.fiche.constate, { date: date(offre.lien_verifie_le) })}
                {offre.lien_etat === "illisible" && ` ${d.fiche.illisibleAide}`}
              </AlertDescription>
            </Alert>
          )}

          <section className="mt-8 rounded-[22px] verre-carte p-6 sm:p-8" aria-labelledby="t-description">
            <h2 id="t-description" className="text-sm text-muted-foreground">
              {d.fiche.description}
            </h2>
            {offre.description ? (
              <div className="mt-4 max-w-[72ch] text-[0.97rem] leading-relaxed whitespace-pre-line">{offre.description}</div>
            ) : (
              <p className="mt-4 text-muted-foreground">{d.fiche.sansDescription}</p>
            )}
          </section>

          {offre.voisines.length > 0 && (
            <section className="mt-10" aria-labelledby="t-voisines">
              <h2 id="t-voisines" className="text-lg font-medium">
                {f(d.fiche.autresOffres, { source: offre.source_nom })}
              </h2>
              <ul className="mt-3 divide-y rounded-[22px] verre-carte ">
                {offre.voisines.map((v) => (
                  <li key={v.id}>
                    <Link href={lienOffre(v.id)} className="flex items-center justify-between gap-4 px-5 py-3.5 text-sm transition-colors hover:bg-muted/60">
                      <span className="line-clamp-1">{v.titre}</span>
                      <span className="shrink-0 text-muted-foreground tabular-nums">{dateCourte(v.date_limite)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="grid content-start gap-4 lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-[22px] verre-carte p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-sm text-muted-foreground">{d.carte.echeance}</h2>
                <p className="mt-1 text-lg">{offre.date_limite ? date(offre.date_limite) : d.commun.nonPrecisee}</p>
                <p className="text-sm text-muted-foreground">{texteEcheance(d, offre.etat_echeance, offre.jours)}</p>
              </div>
              <CompteARebours etat={offre.etat_echeance} jours={offre.jours} dateLimite={offre.date_limite} taille="xl" />
            </div>
            <Meche etat={offre.etat_echeance} jours={offre.jours} className="mt-5 h-1.5" />
            {!offre.date_limite && (
              <p className="mt-4 text-sm text-muted-foreground">
                {d.fiche.sansDate} {(d.fiche.aideSansDate as Record<string, string>)[offre.source] ?? ""}
              </p>
            )}
            <div className="mt-6 border-t pt-6">
              <Consulter
                id={id}
                dejaConsultee={offre.deja_consultee}
                credits={m.credits}
                lienAdmin={m.admin ? offre.lien : null}
                aUnLien={offre.a_un_lien}
              />
              {!ouverte && offre.a_un_lien && (
                <p className="mt-2 text-xs text-muted-foreground">{d.consulter.plusOuverte}</p>
              )}
            </div>
          </div>

          {m.admin && (
            <div className="grid gap-5 rounded-[22px] verre-carte p-6">
              <h2 className="text-sm text-muted-foreground">{d.fiche.administration}</h2>
              <SuiviAdmin id={id} statuts={ref.statuts_suivi} statut={suivi?.statut} note={suivi?.note} />
              <div className="flex flex-wrap gap-2 border-t pt-5">
                <Verdict id={id} pertinent={offre.pertinent} />
                <ModifierEcheance
                  id={id}
                  dateLimite={offre.date_limite}
                  declencheur={
                    <Button variant="outline" size="sm">
                      <CalendarClockIcon /> {d.admin.modifierEcheance}
                    </Button>
                  }
                />
                {offre.lien && <CopierLien lien={offre.lien} />}
              </div>
              {suivi?.decide_par && (
                <p className="text-xs text-muted-foreground">
                  {f(d.fiche.derniereDecision, { qui: suivi.decide_par, date: date(suivi.maj_le) })}
                </p>
              )}
            </div>
          )}

          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 rounded-[22px] verre-carte p-6 text-sm">
            <dt className="text-muted-foreground">{d.fiche.publiee}</dt>
            <dd>{date(offre.date_publication)}</dd>
            <dt className="text-muted-foreground">{d.fiche.collectee}</dt>
            <dd>{date(offre.date_ajout)}</dd>
            {offre.categorie && (
              <>
                <dt className="text-muted-foreground">{d.fiche.categorie}</dt>
                <dd>{offre.categorie}</dd>
              </>
            )}
            {m.admin && offre.raison && (
              <>
                <dt className="text-muted-foreground">{d.fiche.tri}</dt>
                <dd>{offre.raison}</dd>
              </>
            )}
          </dl>
        </aside>
      </div>
    </Panneau>
  )
}
