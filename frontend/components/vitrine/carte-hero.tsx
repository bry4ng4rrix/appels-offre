"use client"

import { motion, useReducedMotion } from "motion/react"
import Link from "next/link"

type Point = { lieu: string; lat: number; lon: number; total: number; urgentes: number }

/** Le moment d'ouverture de la page : les lieux s'allument un a un sur la carte. */
export function CarteHero({ points, libelle, legende }: { points: Point[]; libelle: string; legende: string }) {
  const reduit = useReducedMotion()
  const max = Math.max(1, ...points.map((p) => p.total))
  const tries = [...points].sort((a, b) => b.total - a.total).slice(0, 60)
  return (
    <Link
      href="/carte"
      aria-label={libelle}
      className="group relative block overflow-hidden rounded-[26px] verre-carte "
    >
      <svg viewBox="0 40 2000 680" className="block w-full" aria-hidden>
        <image href="/monde-clair.svg" width={2000} height={800} className="dark:hidden" />
        <image href="/monde-sombre.svg" width={2000} height={800} className="hidden dark:inline" />
        {tries.map((p, i) => {
          const x = ((p.lon + 180) / 360) * 2000
          const y = ((84 - p.lat) / 140) * 800
          const r = 6 + 24 * Math.sqrt(p.total / max)
          return (
            <g key={p.lieu}>
              {i < 10 && p.urgentes > 0 && <circle cx={x} cy={y} r={r} className="onde fill-urgent/35" style={{ animationDelay: `${1 + i * 0.2}s` }} />}
              <motion.circle
                cx={x}
                cy={y}
                r={r}
                className={p.urgentes > 0 ? "fill-ambre/85" : "fill-ambre/45"}
                stroke="var(--card)"
                strokeWidth={2.5}
                initial={reduit ? false : { scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.25 + i * 0.025, type: "spring", stiffness: 260, damping: 18 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              />
            </g>
          )
        })}
      </svg>
      <span className="absolute bottom-3 start-3 flex items-center gap-2 rounded-full verre-carte/90 px-3.5 py-1.5 text-xs backdrop-blur transition-colors group-hover:verre-carte">
        <span className="size-2 rounded-full bg-urgent battement" /> {legende}
      </span>
    </Link>
  )
}
