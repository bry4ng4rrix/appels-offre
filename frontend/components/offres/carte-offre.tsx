import { CalendarDaysIcon, EyeIcon, FileTextIcon, GaugeIcon } from "lucide-react"
import Link from "next/link"

import { BoutonLien } from "@/components/app/bouton-lien"
import { ModifierEcheance, PartagerOffre } from "@/components/offres/actions-admin"
import { PuceEcheance } from "@/components/offres/echeance"
import { IconeSecteur } from "@/components/offres/icone-secteur"
import type { Offre, Suggestion } from "@/lib/api/types"
import { date, nature } from "@/lib/format"

export const lienOffre = (id: string) => `/offres/${id.split("/").map(encodeURIComponent).join("/")}`

function Tuile({ icone, libelle, valeur }: { icone: React.ReactNode; libelle: string; valeur: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-2xl bg-muted px-3 py-2.5">
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icone}
        {libelle}
      </p>
      <p className="mt-1 truncate text-[0.82rem]">{valeur}</p>
    </div>
  )
}

type Props = { offre: Offre | Suggestion; admin?: boolean }

export function CarteOffre({ offre, admin = false }: Props) {
  const score = "score" in offre ? offre.score : null
  const retiree = offre.lien_etat === "introuvable" || offre.lien_etat === "close"
  const href = lienOffre(offre.id)
  const description = [offre.secteur_libelle, offre.pays, retiree ? "retirée par la source" : null].filter(Boolean).join(", ")
  return (
    <article className="verre-carte flex flex-col rounded-[22px] p-4 transition-transform duration-200 hover:-translate-y-0.5">
      <div className="flex items-center gap-2.5 border-b pb-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
          <IconeSecteur code={offre.secteur} className="size-4" />
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-medium" title={offre.organisation ?? undefined}>
          {offre.organisation || offre.source_nom}
        </span>
        <PuceEcheance etat={offre.etat_echeance} jours={offre.jours} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        {score !== null ? (
          <Tuile icone={<GaugeIcon className="size-3.5" />} libelle="Pour vous" valeur={`${score} % de correspondance`} />
        ) : (
          <Tuile icone={<FileTextIcon className="size-3.5" />} libelle="Type" valeur={nature(offre.nature) ?? "Non qualifiée"} />
        )}
        <Tuile icone={<CalendarDaysIcon className="size-3.5" />} libelle="Date limite" valeur={offre.date_limite ? date(offre.date_limite) : "Non précisée"} />
      </div>

      <h3 className="mt-4 line-clamp-2 text-[1.02rem] leading-snug font-normal text-balance">
        <Link href={href} className="hover:underline hover:decoration-border hover:underline-offset-4">
          {offre.titre_lisible}
        </Link>
      </h3>
      <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {description || "Secteur non précisé"}. Source : {offre.source_nom}.
      </p>

      <div className="mt-auto grid grid-cols-2 gap-2 pt-4">
        {admin ? <ModifierEcheance id={offre.id} dateLimite={offre.date_limite} pilule /> : <PartagerOffre href={href} />}
        <BoutonLien href={href} size="lg" className="h-10">
          <EyeIcon /> Voir le détail
        </BoutonLien>
      </div>
    </article>
  )
}

export function GrilleOffres({ offres, admin }: { offres: (Offre | Suggestion)[]; admin?: boolean }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {offres.map((o) => (
        <CarteOffre key={o.id} offre={o} admin={admin} />
      ))}
    </div>
  )
}
