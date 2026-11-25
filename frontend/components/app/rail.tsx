"use client"

import {
  BellIcon,
  BriefcaseBusinessIcon,
  CoinsIcon,
  HouseIcon,
  ListChecksIcon,
  MapIcon,
  SettingsIcon,
  SparklesIcon,
  UsersRoundIcon,
  type LucideIcon,
} from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import { MarqueAO } from "@/components/app/marque"
import { useDico } from "@/components/app/traductions"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Dico } from "@/lib/i18n"
import { LANGUES } from "@/lib/i18n/langues"
import { cn } from "@/lib/utils"

export const ICONES = {
  accueil: HouseIcon,
  pourvous: SparklesIcon,
  offres: BriefcaseBusinessIcon,
  carte: MapIcon,
  taches: ListChecksIcon,
  abonnements: UsersRoundIcon,
  abonnement: CoinsIcon,
  notifications: BellIcon,
  parametres: SettingsIcon,
} satisfies Record<string, LucideIcon>

export type LienNav = { href: string; libelle: string; icone: keyof typeof ICONES; pastille?: number }

/** Le chemin sans prefixe de langue : selon le rendu, Next fournit /offres ou /fr/offres. */
export function sansLangue(pathname: string) {
  return pathname.replace(new RegExp(`^/(${LANGUES.join("|")})(?=/|$)`), "") || "/"
}

export function estActif(chemin: string, href: string) {
  const pathname = sansLangue(chemin)
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`)
}

function Pastille({ n }: { n?: number }) {
  const d = useDico()
  if (!n) return null
  return (
    <span className="absolute -top-0.5 -end-0.5 grid min-w-4.5 place-items-center rounded-full bg-ambre px-1 text-[10px] leading-4.5 font-semibold text-ambre-foreground tabular-nums ring-2 ring-panneau">
      {n}
      <span className="sr-only"> {d.nav.enAttente}</span>
    </span>
  )
}

/** Un lien rond du rail ; le disque sombre glisse vers la page ouverte. */
function LienRond({ lien, actif, groupe }: { lien: LienNav; actif: boolean; groupe: string }) {
  const Icone = ICONES[lien.icone]
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Link
            href={lien.href}
            aria-label={lien.libelle}
            aria-current={actif ? "page" : undefined}
            className={cn(
              "relative grid size-11 place-items-center rounded-full transition-colors",
              actif ? "text-ambre-foreground" : "verre-carte text-muted-foreground hover:text-foreground",
            )}
          />
        }
      >
        {actif && (
          <motion.span layoutId={groupe} className="absolute inset-0 rounded-full bg-ambre shadow-[0_6px_18px_-6px_rgb(235_174_41/0.8)]" transition={{ type: "spring", stiffness: 500, damping: 38 }} />
        )}
        <Icone className="relative size-[18px]" aria-hidden />
        <Pastille n={lien.pastille} />
      </TooltipTrigger>
      <TooltipContent side="right">{lien.libelle}</TooltipContent>
    </Tooltip>
  )
}

export function Rail({ liens, reglages }: { liens: LienNav[]; reglages?: LienNav }) {
  const d = useDico()
  const pathname = usePathname()
  return (
    <aside className="sticky top-4 hidden h-[calc(100dvh-2rem)] w-[72px] shrink-0 flex-col items-center verre rounded-[36px] py-4 md:flex">
      <Link href="/" aria-label={d.nav.accueilLien} className="rounded-full">
        <MarqueAO className="size-12" />
      </Link>
      <nav aria-label={d.nav.principale} className="my-auto flex flex-col gap-2.5">
        {liens.map((l) => (
          <LienRond key={l.href} lien={l} actif={estActif(pathname, l.href)} groupe="rail" />
        ))}
      </nav>
      {reglages && <LienRond lien={reglages} actif={estActif(pathname, reglages.href)} groupe="rail" />}
    </aside>
  )
}

/** Sur telephone, le rail devient une barre flottante en bas de l'ecran. */
export function BarreMobile({ liens }: { liens: LienNav[] }) {
  const d = useDico()
  const pathname = usePathname()
  return (
    <nav
      aria-label={d.nav.principale}
      className="fixed inset-x-3 bottom-3 z-40 flex justify-around verre rounded-full p-1.5 md:hidden"
    >
      {liens.slice(0, 5).map((l) => {
        const actif = estActif(pathname, l.href)
        const Icone = ICONES[l.icone]
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-label={l.libelle}
            aria-current={actif ? "page" : undefined}
            className={cn("relative grid size-11 place-items-center rounded-full", actif ? "text-ambre-foreground" : "text-muted-foreground")}
          >
            {actif && <motion.span layoutId="mobile" className="absolute inset-0 rounded-full bg-ambre" />}
            <Icone className="relative size-5" aria-hidden />
            <Pastille n={l.pastille} />
          </Link>
        )
      })}
    </nav>
  )
}

const TITRES: [RegExp, keyof Dico["titres"]][] = [
  [/^\/$/, "accueil"],
  [/^\/offres\/.+/, "fiche"],
  [/^\/offres/, "offres"],
  [/^\/pour-vous/, "pourVous"],
  [/^\/carte/, "carte"],
  [/^\/profil/, "profil"],
  [/^\/notifications/, "notifications"],
  [/^\/abonnement/, "abonnement"],
  [/^\/compte/, "motDePasse"],
  [/^\/admin\/taches/, "taches"],
  [/^\/admin\/abonnements/, "abonnements"],
  [/^\/admin\/parametres/, "parametres"],
]

/** Le titre de la barre du haut suit la page ouverte. */
export function TitrePage() {
  const d = useDico()
  const pathname = sansLangue(usePathname())
  const cle = TITRES.find(([motif]) => motif.test(pathname))?.[1] ?? "defaut"
  return <h1 className="truncate text-2xl font-normal tracking-tight sm:text-[1.7rem]">{d.titres[cle]}</h1>
}
