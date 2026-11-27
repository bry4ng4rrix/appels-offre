import { CheckIcon } from "lucide-react"

import type { Plan } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f } from "@/lib/i18n"
import { dico } from "@/lib/i18n/serveur"
import { cn } from "@/lib/utils"

/** Un plan en carte de tarif. Le texte vient des champs du plan (administration). */
export async function CartePlan({ plan, vedette, action }: { plan: Plan; vedette?: boolean; action: React.ReactNode }) {
  const d = await dico()
  const { euro } = formateurs(d.locale)
  const p = d.plan
  const inclus = [
    f(plan.par_jour ? p.parJour : p.enReserve, { n: plan.credits }),
    plan.duree_jours ? f(p.pendant, { j: plan.duree_jours }) : p.sansLimite,
    f(p.prixCredit, { prix: euro(plan.prix_credit) }),
  ]
  return (
    <div
      className={cn(
        "relative flex flex-col rounded-[22px] verre-carte p-6",
        vedette && "shadow-[0_20px_50px_-24px_color-mix(in_oklab,var(--ambre)_70%,transparent)] ring-2 ring-ambre/60",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-medium">{plan.nom}</h3>
        {vedette && <span className="rounded-full bg-ambre px-2.5 py-0.5 text-xs font-medium text-ambre-foreground">{p.recommande}</span>}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {plan.par_jour
          ? plan.duree_jours ? f(p.descJourDuree, { j: plan.duree_jours }) : p.descJour
          : p.descLot}
      </p>
      <p className="mt-6 flex items-baseline gap-2">
        <span className="font-chiffres text-5xl leading-none font-light">{euro(plan.prix)}</span>
        <span className="text-sm text-muted-foreground">{plan.par_jour && plan.duree_jours ? f(p.parDuree, { j: plan.duree_jours }) : p.uneFois}</span>
      </p>
      <div className="mt-6">{action}</div>
      <ul className="mt-6 grid gap-2.5 text-sm" aria-label={p.inclus}>
        {inclus.map((l) => (
          <li key={l} className="flex gap-2.5">
            <CheckIcon className="mt-0.5 size-4 shrink-0 text-marque" aria-hidden />
            {l}
          </li>
        ))}
      </ul>
    </div>
  )
}
