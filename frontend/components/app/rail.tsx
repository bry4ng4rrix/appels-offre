"use client"

import {
  BellIcon,
  BriefcaseBusinessIcon,
  ClipboardCheckIcon,
  CoinsIcon,
  HouseIcon,
  ListChecksIcon,
  MapIcon,
  MoonIcon,
  SettingsIcon,
  SparklesIcon,
  SunIcon,
  UsersRoundIcon,
  type LucideIcon,
} from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

import { Tuile } from "@/components/app/marque"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export const ICONES = {
  accueil: HouseIcon,
  pourvous: SparklesIcon,
  offres: BriefcaseBusinessIcon,
  carte: MapIcon,
  suivi: ClipboardCheckIcon,
  taches: ListChecksIcon,
  abonnements: UsersRoundIcon,
  abonnement: CoinsIcon,
  notifications: BellIcon,
  parametres: SettingsIcon,
} satisfies Record<string, LucideIcon>

export type LienNav = { href: string; libelle: string; icone: keyof typeof ICONES; pastille?: number }

export function estActif(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`)
}

function Pastille({ n }: { n?: number }) {
  if (!n) return null
  return (
    <span className="absolute -top-0.5 -right-0.5 grid min-w-4.5 place-items-center rounded-full bg-lavande px-1 text-[10px] leading-4.5 font-semibold text-white tabular-nums ring-2 ring-panneau">
      {n}
      <span className="sr-only"> en attente</span>
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
              actif ? "text-primary-foreground" : "bg-card text-muted-foreground shadow-xs hover:text-foreground",
            )}
          />
        }
      >
        {actif && (
          <motion.span layoutId={groupe} className="absolute inset-0 rounded-full bg-primary" transition={{ type: "spring", stiffness: 500, damping: 38 }} />
        )}
        <Icone className="relative size-[18px]" aria-hidden />
        <Pastille n={lien.pastille} />
      </TooltipTrigger>
      <TooltipContent side="right">{lien.libelle}</TooltipContent>
    </Tooltip>
  )
}

/** Clair ou sombre : deux disques empiles, celui du theme actif ressort. */
function ThemeRail() {
  const { resolvedTheme, setTheme } = useTheme()
  const [monte, setMonte] = useState(false)
  useEffect(() => setMonte(true), [])
  const sombre = monte && resolvedTheme === "dark"
  return (
    <div className="flex flex-col gap-1 rounded-full bg-secondary p-1" role="group" aria-label="Thème">
      {[
        { code: "dark", Icone: MoonIcon, libelle: "Thème sombre", actif: sombre },
        { code: "light", Icone: SunIcon, libelle: "Thème clair", actif: monte && !sombre },
      ].map(({ code, Icone, libelle, actif }) => (
        <button
          key={code}
          type="button"
          aria-label={libelle}
          aria-pressed={actif}
          onClick={() => setTheme(code)}
          className={cn(
            "grid size-9 place-items-center rounded-full transition-colors",
            actif ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Icone className="size-4" />
        </button>
      ))}
    </div>
  )
}

export function Rail({ liens, reglages }: { liens: LienNav[]; reglages?: LienNav }) {
  const pathname = usePathname()
  return (
    <aside className="sticky top-4 hidden h-[calc(100dvh-2rem)] w-[72px] shrink-0 flex-col items-center rounded-[36px] bg-panneau py-4 md:flex">
      <Link href="/" aria-label="Label Collectes, accueil" className="rounded-full">
        <Tuile className="size-12 rounded-full" />
      </Link>
      <nav aria-label="Navigation principale" className="my-auto flex flex-col gap-2.5">
        {liens.map((l) => (
          <LienRond key={l.href} lien={l} actif={estActif(pathname, l.href)} groupe="rail" />
        ))}
      </nav>
      <div className="flex flex-col items-center gap-3">
        <ThemeRail />
        {reglages && <LienRond lien={reglages} actif={estActif(pathname, reglages.href)} groupe="rail" />}
      </div>
    </aside>
  )
}

/** Sur telephone, le rail devient une barre flottante en bas de l'ecran. */
export function BarreMobile({ liens }: { liens: LienNav[] }) {
  const pathname = usePathname()
  return (
    <nav
      aria-label="Navigation principale"
      className="fixed inset-x-3 bottom-3 z-40 flex justify-around rounded-full bg-panneau/95 p-1.5 shadow-lg ring-1 ring-border backdrop-blur md:hidden"
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
            className={cn("relative grid size-11 place-items-center rounded-full", actif ? "text-primary-foreground" : "text-muted-foreground")}
          >
            {actif && <motion.span layoutId="mobile" className="absolute inset-0 rounded-full bg-primary" />}
            <Icone className="relative size-5" aria-hidden />
            <Pastille n={l.pastille} />
          </Link>
        )
      })}
    </nav>
  )
}

const TITRES: [RegExp, string][] = [
  [/^\/$/, "Accueil"],
  [/^\/offres\/.+/, "Fiche de l'offre"],
  [/^\/offres/, "Offres"],
  [/^\/pour-vous/, "Pour vous"],
  [/^\/carte/, "Carte des offres"],
  [/^\/profil/, "Mon profil"],
  [/^\/notifications/, "Notifications"],
  [/^\/abonnement/, "Abonnement"],
  [/^\/compte/, "Mot de passe"],
  [/^\/admin\/suivi/, "Suivi commercial"],
  [/^\/admin\/taches/, "Tâches"],
  [/^\/admin\/abonnements/, "Abonnements"],
  [/^\/admin\/parametres/, "Paramètres"],
]

/** Le titre de la barre du haut suit la page ouverte. */
export function TitrePage() {
  const pathname = usePathname()
  const titre = TITRES.find(([motif]) => motif.test(pathname))?.[1] ?? "Label Collectes"
  return <h1 className="truncate text-2xl font-normal tracking-tight sm:text-[1.7rem]">{titre}</h1>
}
