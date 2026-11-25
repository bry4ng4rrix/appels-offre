"use client"

import { CheckIcon, LanguagesIcon } from "lucide-react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useTransition } from "react"

import { useDico, useLangue } from "@/components/app/traductions"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { changerLangue } from "@/lib/actions/langue"
import { DRAPEAUX, LANGUES, NOMS, type Langue } from "@/lib/i18n/langues"
import { cn } from "@/lib/utils"

/** Le choix de langue : un menu, chaque langue ecrite dans sa propre langue. */
export function ChoixLangue({ className }: { className?: string }) {
  const actuelle = useLangue()
  const d = useDico()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const [enCours, demarrer] = useTransition()

  function choisir(l: Langue) {
    if (l === actuelle) return
    demarrer(async () => {
      await changerLangue(l)
      // Une adresse prefixee (/en/...) imposerait encore l'ancienne langue : on la retire.
      const chemin = pathname.replace(new RegExp(`^/(${LANGUES.join("|")})(?=/|$)`), "") || "/"
      const recherche = params.toString()
      router.replace(recherche ? `${chemin}?${recherche}` : chemin, { scroll: false })
    })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={d.langue.choisir}
        className={cn(
          "verre-carte inline-flex h-10 items-center gap-1.5 rounded-full px-3 text-sm text-muted-foreground transition-colors hover:text-foreground",
          enCours && "opacity-60",
          className,
        )}
      >
        <LanguagesIcon className="size-[18px]" aria-hidden />
        <span className="font-medium uppercase">{actuelle}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-[min(28rem,70vh)] w-52 overflow-y-auto">
        <DropdownMenuGroup>
          <DropdownMenuLabel>{d.langue.choisir}</DropdownMenuLabel>
          {LANGUES.map((l) => (
            <DropdownMenuItem key={l} onClick={() => choisir(l)} lang={l}>
              <span aria-hidden className="text-base leading-none">{DRAPEAUX[l]}</span>
              <span className="flex-1">{NOMS[l]}</span>
              {l === actuelle && <CheckIcon className="size-4" />}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
