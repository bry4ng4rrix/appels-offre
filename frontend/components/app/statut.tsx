import { cn } from "@/lib/utils"

const TONS = {
  succes: "bg-lointaine/10 text-lointaine",
  attente: "bg-proche/10 text-proche",
  erreur: "bg-urgent/10 text-urgent",
  neutre: "bg-muted text-muted-foreground",
  info: "bg-accent text-accent-foreground",
} as const

export type TonStatut = keyof typeof TONS

export function Statut({ ton, children }: { ton: TonStatut; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap", TONS[ton])}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {children}
    </span>
  )
}

/** Etat d'un abonnement (champ `etat` de l'API : attente, actif, termine, refuse). */
export function tonAbonnement(etat: string): TonStatut {
  if (etat === "actif") return "succes"
  if (etat === "attente") return "attente"
  if (etat === "refuse") return "erreur"
  return "neutre"
}

export const LIBELLES_ABONNEMENT: Record<string, string> = {
  actif: "Actif",
  termine: "Terminé",
  attente: "En attente",
  refuse: "Refusé",
}
