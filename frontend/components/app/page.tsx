import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import Link from "next/link"

import { Skeleton } from "@/components/ui/skeleton"
import { f } from "@/lib/i18n"
import { dico } from "@/lib/i18n/serveur"
import { cn } from "@/lib/utils"

export function EnTetePage({
  titre,
  children,
  actions,
  className,
}: {
  titre: React.ReactNode
  children?: React.ReactNode
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="max-w-2xl">
        <h2 className="text-xl font-medium tracking-tight text-balance sm:text-[1.4rem]">{titre}</h2>
        {children && <div className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{children}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

/** Pagination par liens : l'URL reste la source de verite (partageable, bouton retour). */
export async function Pagination({
  page,
  pages,
  total,
  parPage,
  href,
}: {
  page: number
  pages: number
  total: number
  parPage: number
  href: (page: number) => string
}) {
  if (pages <= 1) return null
  const d = await dico()
  const debut = (page - 1) * parPage + 1
  const fin = Math.min(total, page * parPage)
  const bouton = "inline-flex h-10 items-center gap-1 rounded-full verre-carte px-4 text-sm shadow-xs transition-colors hover:bg-muted"
  return (
    <nav aria-label={d.pagination.aria} className="mt-10 flex items-center justify-between gap-4">
      <p className="text-sm text-muted-foreground tabular-nums">
        {f(d.pagination.plage, { debut, fin, total: total.toLocaleString(d.locale) })}
      </p>
      <div className="flex gap-2">
        {page > 1 && (
          <Link className={bouton} href={href(page - 1)} rel="prev">
            <ChevronLeftIcon className="size-4 rtl:rotate-180" /> {d.pagination.precedent}
          </Link>
        )}
        <span className="inline-flex h-9 items-center px-2 text-sm text-muted-foreground tabular-nums">
          {page} / {pages}
        </span>
        {page < pages && (
          <Link className={bouton} href={href(page + 1)} rel="next">
            {d.pagination.suivant} <ChevronRightIcon className="size-4 rtl:rotate-180" />
          </Link>
        )}
      </div>
    </nav>
  )
}

/** Etat vide : dit quoi faire, pas seulement ce qui manque. */
export function Vide({ titre, children, action }: { titre: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mt-8 flex flex-col items-center rounded-[22px] verre-carte px-6 py-16 text-center ">
      <svg viewBox="0 0 120 64" className="mb-6 h-16 w-32 text-muted-foreground/40" aria-hidden>
        <rect x="8" y="10" width="64" height="44" rx="6" fill="none" stroke="currentColor" strokeWidth="2.5" />
        <path d="M20 26h40M20 36h28" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="86" cy="34" r="16" fill="none" stroke="var(--marque)" strokeWidth="3" />
        <path d="M98 46l12 12" stroke="var(--marque)" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <p className="text-lg font-medium">{titre}</p>
      {children && <p className="mt-2 max-w-md text-sm text-muted-foreground">{children}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export function GrilleSquelette({ n = 6 }: { n?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="flex h-64 flex-col gap-3 rounded-[22px] verre-carte p-4 ">
          <div className="flex justify-between">
            <Skeleton className="h-5 w-32 rounded-full" />
            <Skeleton className="h-10 w-14" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="mt-auto h-1 w-full" />
        </div>
      ))}
    </div>
  )
}

/** Construit une URL de la page courante en changeant quelques parametres. */
export function avecParams(base: string, actuels: Record<string, string | undefined>, changes: Record<string, string | number | undefined>) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries({ ...actuels, ...changes })) if (v !== undefined && v !== "") p.set(k, String(v))
  const s = p.toString()
  return s ? `${base}?${s}` : base
}

/** searchParams de Next (string | string[]) ramenes a de simples chaines. */
export function aplatir(sp: Record<string, string | string[] | undefined>): Record<string, string | undefined> {
  return Object.fromEntries(Object.entries(sp).map(([k, v]) => [k, Array.isArray(v) ? v[0] : v]))
}
