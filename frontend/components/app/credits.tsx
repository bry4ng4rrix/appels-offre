"use client"

import { CoinsIcon } from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"

import { NombreAnime } from "@/components/app/nombre-anime"
import { useDico } from "@/components/app/traductions"
import type { Credits } from "@/lib/api/types"
import { f } from "@/lib/i18n"
import { cn } from "@/lib/utils"

/** Le compteur de l'en-tete : l'icone seule, le chiffre au survol. Le chiffre reste visible
 *  a zero, sur ecran tactile (pointer: coarse), et deux secondes apres chaque debit pour qu'on le voie rouler. */
export function PastilleCredits({ credits }: { credits: Credits }) {
  const d = useDico()
  const total = credits.total ?? 0
  const vide = total === 0
  const [precedent, setPrecedent] = useState(total)
  const [revele, setRevele] = useState(false)
  if (total !== precedent) {
    setPrecedent(total)
    setRevele(true)
  }
  useEffect(() => {
    if (!revele) return
    const minuteur = setTimeout(() => setRevele(false), 2200)
    return () => clearTimeout(minuteur)
  }, [revele, total])

  const visible = vide || revele
  return (
    <Link
      href="/abonnement"
      aria-label={f(new Intl.PluralRules(d.locale).select(total) === "one" ? d.credits.restants_un : d.credits.restants, { n: total })}
      className="group verre-carte inline-flex h-10 items-center rounded-full p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <span className={cn("grid size-8 place-items-center rounded-full", vide ? "bg-urgent text-sur-vif" : "bg-ambre text-ambre-foreground")}>
        <CoinsIcon className="size-4" aria-hidden />
      </span>
      {/* grid-cols 0fr -> 1fr : la largeur s'anime jusqu'a celle du chiffre, quelle qu'elle soit. */}
      <span
        aria-hidden
        className={cn(
          "grid transition-[grid-template-columns,opacity] duration-300 ease-out",
          "pointer-coarse:grid-cols-[1fr] pointer-coarse:opacity-100",
          visible
            ? "grid-cols-[1fr] opacity-100"
            : "grid-cols-[0fr] opacity-0 group-hover:grid-cols-[1fr] group-hover:opacity-100 group-focus-visible:grid-cols-[1fr] group-focus-visible:opacity-100",
        )}
      >
        <span className={cn("min-w-0 overflow-hidden text-base font-medium", vide && "text-urgent")}>
          <span className="block px-2.5">
            <NombreAnime valeur={total} />
          </span>
        </span>
      </span>
    </Link>
  )
}
