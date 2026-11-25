"use client"

import { CoinsIcon } from "lucide-react"
import Link from "next/link"

import { NombreAnime } from "@/components/app/nombre-anime"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Credits } from "@/lib/api/types"
import { cn } from "@/lib/utils"

/** Le compteur de l'en-tete. Il roule quand une annonce est ouverte (la page se rafraichit). */
export function PastilleCredits({ credits }: { credits: Credits }) {
  const total = credits.total ?? 0
  const vide = total === 0
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Link
            href="/abonnement"
            className={cn(
              "inline-flex h-10 items-center gap-2 rounded-full bg-card pr-3.5 pl-1 text-sm shadow-xs transition-colors",
              vide ? "text-urgent" : "hover:bg-accent",
            )}
          />
        }
      >
        <span className={cn("grid size-8 place-items-center rounded-full text-white", vide ? "bg-urgent" : "bg-lavande")}>
          <CoinsIcon className="size-4" aria-hidden />
        </span>
        <span className="font-chiffres text-base font-medium">
          <NombreAnime valeur={total} />
        </span>
        <span className="hidden sm:inline">{total > 1 ? "crédits" : "crédit"}</span>
      </TooltipTrigger>
      <TooltipContent>
        {credits.du_jour} du jour sur {credits.gratuits_par_jour}
        {!!credits.lots && `, ${credits.lots} en réserve`}. Cliquez pour en obtenir plus.
      </TooltipContent>
    </Tooltip>
  )
}
