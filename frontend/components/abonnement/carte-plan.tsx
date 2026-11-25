import { CheckIcon } from "lucide-react"

import type { Plan } from "@/lib/api/types"
import { ariary, entier } from "@/lib/format"
import { cn } from "@/lib/utils"

/** Un plan en carte de tarif. Le texte vient des champs du plan (administration). */
export function CartePlan({ plan, gratuits, vedette, action }: { plan: Plan; gratuits: number; vedette?: boolean; action: React.ReactNode }) {
  const inclus = plan.par_jour
    ? [`+${plan.credits} crédits chaque jour`, `${plan.credits + gratuits} annonces par jour avec vos ${gratuits} gratuites`]
    : [`+${plan.credits} crédits en réserve`, `Utilisés une fois vos ${gratuits} crédits du jour épuisés`]
  inclus.push(plan.duree_jours ? `Pendant ${plan.duree_jours} jours` : "Sans date limite", `Soit ${ariary(plan.prix_credit)} le crédit`)
  return (
    <div
      className={cn(
        "relative flex flex-col rounded-[22px] bg-card ring-1 ring-border/70 p-6",
        vedette && "shadow-[0_20px_50px_-24px_color-mix(in_oklab,var(--lavande)_70%,transparent)] ring-2 ring-lavande/60",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-medium">{plan.nom}</h3>
        {vedette && <span className="rounded-full bg-lavande px-2.5 py-0.5 text-xs font-medium text-white">Recommandé</span>}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {plan.par_jour
          ? `Plus de crédits chaque jour${plan.duree_jours ? `, pendant ${plan.duree_jours} jours` : ""}.`
          : "Un lot de crédits, à utiliser quand vous voulez."}
      </p>
      <p className="mt-6 flex items-baseline gap-2">
        <span className="font-chiffres text-5xl leading-none font-light">{entier(plan.prix)}</span>
        <span className="text-xl">Ar</span>
        <span className="text-sm text-muted-foreground">{plan.par_jour && plan.duree_jours ? `/ ${plan.duree_jours} jours` : "une fois"}</span>
      </p>
      <div className="mt-6">{action}</div>
      <ul className="mt-6 grid gap-2.5 text-sm" aria-label="Inclus">
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
