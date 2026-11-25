import { FlagIcon } from "lucide-react"

import type { EtatEcheance } from "@/lib/api/types"
import { f, pl, type Dico } from "@/lib/i18n"
import { dico } from "@/lib/i18n/serveur"
import { consume, formateurs, ton, type Ton } from "@/lib/format"
import { cn } from "@/lib/utils"

const TEXTE: Record<Ton, string> = {
  urgent: "text-urgent",
  proche: "text-proche",
  lointaine: "text-lointaine",
  neutre: "text-muted-foreground",
}
type Props = { etat: EtatEcheance; jours: number; dateLimite?: string | null; taille?: "md" | "xl" }

/** Le compte a rebours, signature de l'app : « J-4 » en chiffres d'affiche, couleur d'urgence. */
export async function CompteARebours({ etat, jours, dateLimite, taille = "md" }: Props) {
  const d = await dico()
  const { dateCourte } = formateurs(d.locale)
  const t = ton(etat)
  const grand = taille === "xl" ? "text-6xl" : "text-4xl"
  const ouverte = etat === "urgente" || etat === "proche" || etat === "lointaine"
  let principal: React.ReactNode
  let legende: string
  if (ouverte && jours === 0) {
    principal = <span className={cn("font-chiffres leading-none font-light", grand)}>{d.echeance.auj}</span>
    legende = d.echeance.dernierJour
  } else if (ouverte) {
    principal = (
      <span className="flex items-baseline leading-none">
        <span className={cn("font-medium", taille === "xl" ? "text-2xl" : "text-base")}>{d.echeance.prefixe}</span>
        <span className={cn("font-chiffres font-light", grand)}>{jours}</span>
      </span>
    )
    legende = dateCourte(dateLimite)
  } else if (etat === "passee") {
    principal = <span className={cn("leading-none font-light", taille === "xl" ? "text-5xl" : "text-2xl")}>{d.echeance.close}</span>
    legende = dateCourte(dateLimite)
  } else {
    principal = <span className={cn("leading-none font-light", taille === "xl" ? "text-5xl" : "text-2xl")}>—</span>
    legende = etat === "presumee" ? d.echeance.presumeeClose : d.echeance.sansDate
  }
  return (
    <div className={cn("flex shrink-0 flex-col items-end gap-1 text-end", TEXTE[t])}>
      <span className="flex items-center gap-1.5">
        {ouverte && jours <= 3 && <span className="size-2 rounded-full bg-current battement" aria-hidden />}
        {principal}
      </span>
      <span className="text-xs font-medium text-muted-foreground">{legende}</span>
    </div>
  )
}

/** La meche : la part des 30 derniers jours deja consumee avant l'echeance. */
export async function Meche({ etat, jours, className }: { etat: EtatEcheance; jours: number; className?: string }) {
  const d = await dico()
  return (
    <div
      className={cn("h-1 w-full overflow-hidden rounded-full bg-muted", className)}
      role="progressbar"
      aria-label={d.echeance.jauge}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(consume(jours, etat))}
    >
      <div className="meche degrade h-full rounded-full" style={{ width: `${consume(jours, etat)}%` }} />
    </div>
  )
}

export function texteEcheance(d: Dico, etat: EtatEcheance, jours: number) {
  if (etat === "passee") return d.echeance.passee
  if (etat === "inconnue") return f(d.echeance.inconnue, { j: jours })
  if (etat === "presumee") return f(d.echeance.presumee, { j: jours })
  if (jours === 0) return d.echeance.clotureAuj
  return f(pl(d, jours, d.echeance.dans_un, d.echeance.dans), { j: jours })
}

const PUCE: Record<Ton, string> = {
  urgent: "border-urgent/25 bg-urgent/8 text-urgent",
  proche: "border-proche/25 bg-proche/8 text-proche",
  lointaine: "border-lointaine/25 bg-lointaine/8 text-lointaine",
  neutre: "border-border bg-muted text-muted-foreground",
}

/** La puce drapeau des cartes : l'urgence en un coup d'oeil. */
export async function PuceEcheance({ etat, jours }: { etat: EtatEcheance; jours: number }) {
  const d = await dico()
  const t = ton(etat)
  const ouverte = etat === "urgente" || etat === "proche" || etat === "lointaine"
  const texte = ouverte ? (jours === 0 ? d.echeance.aujourdhui : `${d.echeance.prefixe}${jours}`) : etat === "passee" ? d.echeance.close : d.echeance.sansDateMaj
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium tabular-nums", PUCE[t])}>
      {ouverte && jours <= 3 ? <span className="size-1.5 rounded-full bg-current battement" aria-hidden /> : <FlagIcon className="size-3" aria-hidden />}
      {texte}
    </span>
  )
}
