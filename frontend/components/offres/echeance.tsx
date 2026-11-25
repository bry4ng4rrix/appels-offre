import { FlagIcon } from "lucide-react"

import type { EtatEcheance } from "@/lib/api/types"
import { consume, dateCourte, ton, type Ton } from "@/lib/format"
import { cn } from "@/lib/utils"

const TEXTE: Record<Ton, string> = {
  urgent: "text-urgent",
  proche: "text-proche",
  lointaine: "text-lointaine",
  neutre: "text-muted-foreground",
}
const FOND: Record<Ton, string> = {
  urgent: "bg-urgent",
  proche: "bg-proche",
  lointaine: "bg-lointaine",
  neutre: "bg-muted-foreground/40",
}

type Props = { etat: EtatEcheance; jours: number; dateLimite?: string | null; taille?: "md" | "xl" }

/** Le compte a rebours, signature de l'app : « J-4 » en chiffres d'affiche, couleur d'urgence. */
export function CompteARebours({ etat, jours, dateLimite, taille = "md" }: Props) {
  const t = ton(etat)
  const grand = taille === "xl" ? "text-6xl" : "text-4xl"
  const ouverte = etat === "urgente" || etat === "proche" || etat === "lointaine"
  let principal: React.ReactNode
  let legende: string
  if (ouverte && jours === 0) {
    principal = <span className={cn("font-chiffres leading-none font-light", grand)}>Auj.</span>
    legende = "dernier jour"
  } else if (ouverte) {
    principal = (
      <span className="flex items-baseline leading-none">
        <span className={cn("font-medium", taille === "xl" ? "text-2xl" : "text-base")}>J-</span>
        <span className={cn("font-chiffres font-light", grand)}>{jours}</span>
      </span>
    )
    legende = dateCourte(dateLimite)
  } else if (etat === "passee") {
    principal = <span className={cn("leading-none font-light", taille === "xl" ? "text-5xl" : "text-2xl")}>Close</span>
    legende = dateCourte(dateLimite)
  } else {
    principal = <span className={cn("leading-none font-light", taille === "xl" ? "text-5xl" : "text-2xl")}>—</span>
    legende = etat === "presumee" ? "présumée close" : "sans date"
  }
  return (
    <div className={cn("flex shrink-0 flex-col items-end gap-1 text-right", TEXTE[t])}>
      <span className="flex items-center gap-1.5">
        {ouverte && jours <= 3 && <span className="size-2 rounded-full bg-current battement" aria-hidden />}
        {principal}
      </span>
      <span className="text-xs font-medium text-muted-foreground">{legende}</span>
    </div>
  )
}

/** La meche : la part des 30 derniers jours deja consumee avant l'echeance. */
export function Meche({ etat, jours, className }: { etat: EtatEcheance; jours: number; className?: string }) {
  const t = ton(etat)
  return (
    <div
      className={cn("h-1 w-full overflow-hidden rounded-full bg-muted", className)}
      role="progressbar"
      aria-label="Temps écoulé avant l'échéance"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(consume(jours, etat))}
    >
      <div className={cn("meche h-full rounded-full", FOND[t])} style={{ width: `${consume(jours, etat)}%` }} />
    </div>
  )
}

export function texteEcheance(etat: EtatEcheance, jours: number) {
  if (etat === "passee") return "Échéance passée"
  if (etat === "inconnue") return `Sans date limite, publiée il y a ${jours} j`
  if (etat === "presumee") return `Présumée close, publiée il y a ${jours} j`
  if (jours === 0) return "Clôture aujourd'hui"
  return `Clôture dans ${jours} jour${jours > 1 ? "s" : ""}`
}

const PUCE: Record<Ton, string> = {
  urgent: "border-urgent/25 bg-urgent/8 text-urgent",
  proche: "border-proche/25 bg-proche/8 text-proche",
  lointaine: "border-lointaine/25 bg-lointaine/8 text-lointaine",
  neutre: "border-border bg-muted text-muted-foreground",
}

/** La puce drapeau des cartes : l'urgence en un coup d'oeil. */
export function PuceEcheance({ etat, jours }: { etat: EtatEcheance; jours: number }) {
  const t = ton(etat)
  const ouverte = etat === "urgente" || etat === "proche" || etat === "lointaine"
  const texte = ouverte ? (jours === 0 ? "Aujourd'hui" : `J-${jours}`) : etat === "passee" ? "Close" : "Sans date"
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium tabular-nums", PUCE[t])}>
      {ouverte && jours <= 3 ? <span className="size-1.5 rounded-full bg-current battement" aria-hidden /> : <FlagIcon className="size-3" aria-hidden />}
      {texte}
    </span>
  )
}
