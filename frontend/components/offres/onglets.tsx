"use client"

import {
  ArchiveIcon,
  BookmarkCheckIcon,
  CalendarOffIcon,
  CircleSlashIcon,
  FilterXIcon,
  LayersIcon,
  ZapIcon,
  type LucideIcon,
} from "lucide-react"
import Link from "next/link"

import { cn } from "@/lib/utils"

const ICONES: Record<string, LucideIcon> = {
  toutes: LayersIcon,
  actionnables: ZapIcon,
  retenues: BookmarkCheckIcon,
  "sans-echeance": CalendarOffIcon,
  cloturees: ArchiveIcon,
  retirees: CircleSlashIcon,
  ecartees: FilterXIcon,
}

export type Onglet = { code: string; libelle: string; href: string; nombre?: number }

/** Onglets en intercalaires : l'onglet ouvert se soude au panneau qui suit.
 *  Ce sont des liens : changer d'onglet garde les autres filtres. */
export function Onglets({ onglets, actif }: { onglets: Onglet[]; actif: string }) {
  return (
    <nav aria-label="Affichage" className="-mb-px flex items-end gap-1.5 overflow-x-auto pr-4 [scrollbar-width:none]">
      {onglets.map((o) => {
        const courant = o.code === actif
        const Icone = ICONES[o.code] ?? LayersIcon
        return (
          <Link
            key={o.code}
            href={o.href}
            scroll={false}
            aria-current={courant ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2.5 py-2 pr-3 pl-2 text-sm whitespace-nowrap transition-colors",
              courant
                ? "rounded-t-[22px] bg-panneau pb-3.5 text-foreground"
                : "mb-1.5 rounded-full bg-panneau/55 text-muted-foreground hover:bg-panneau/85 hover:text-foreground",
            )}
          >
            <span
              className={cn(
                "grid size-8 place-items-center rounded-full",
                courant ? "bg-lavande text-white" : "bg-card text-muted-foreground",
              )}
            >
              <Icone className="size-4" aria-hidden />
            </span>
            {o.libelle}
            {o.nombre !== undefined && (
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs tabular-nums",
                  courant ? "bg-lavande/15 text-accent-foreground" : "bg-card",
                )}
              >
                {o.nombre.toLocaleString("fr-FR")}
              </span>
            )}
          </Link>
        )
      })}
    </nav>
  )
}
