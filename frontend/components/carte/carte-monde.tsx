"use client"

import { AnimatePresence, motion } from "motion/react"
import { ArrowRightIcon, MinusIcon, PlusIcon, RotateCcwIcon, XIcon } from "lucide-react"
import Link from "next/link"
import { useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { lienOffre } from "@/components/offres/carte-offre"
import { cn } from "@/lib/utils"

export type Point = {
  lieu: string
  lat: number
  lon: number
  total: number
  marches: number
  emplois: number
  urgentes: number
  exemples?: { id: string; titre: string }[]
}

// Meme projection que le fond de carte (equirectangulaire, 84 N a 56 S, 2000 x 800).
const L = 2000
const H = 800
const projeter = (lat: number, lon: number) => ({ x: ((lon + 180) / 360) * L, y: ((84 - lat) / 140) * H })
const VUE_INITIALE = { x: 0, y: 0, w: L, h: H }
const fr = new Intl.NumberFormat("fr-FR")

type Props = { points: Point[]; connecte: boolean; parametres: string }

export function CarteMonde({ points, connecte, parametres }: Props) {
  const [vue, setVue] = useState(VUE_INITIALE)
  const [choisi, setChoisi] = useState<Point | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const glisse = useRef<{ x: number; y: number; vx: number; vy: number; bouge: boolean } | null>(null)

  const max = Math.max(1, ...points.map((p) => p.total))
  // Les plus gros dessous, pour que les petits restent cliquables.
  const tries = useMemo(() => [...points].sort((a, b) => b.total - a.total), [points])
  const pressants = useMemo(() => new Set(tries.filter((p) => p.urgentes > 0).slice(0, 14).map((p) => p.lieu)), [tries])
  const echelle = vue.w / L

  function zoomer(facteur: number, cx = vue.x + vue.w / 2, cy = vue.y + vue.h / 2) {
    const w = Math.min(L, Math.max(L / 12, vue.w * facteur))
    const h = (w / L) * H
    setVue({ x: cx - (cx - vue.x) * (w / vue.w), y: cy - (cy - vue.y) * (h / vue.h), w, h })
  }

  function versSvg(e: { clientX: number; clientY: number }) {
    const r = svg.current!.getBoundingClientRect()
    return { x: vue.x + ((e.clientX - r.left) / r.width) * vue.w, y: vue.y + ((e.clientY - r.top) / r.height) * vue.h }
  }

  const lienOffres = (lieu: string) => {
    const p = new URLSearchParams(parametres)
    p.set("lieu", lieu)
    return `/offres?${p}`
  }

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="relative overflow-hidden rounded-[26px] verre-carte ">
        <svg
          ref={svg}
          viewBox={`${vue.x} ${vue.y} ${vue.w} ${vue.h}`}
          className="block aspect-[5/2] w-full cursor-grab touch-none select-none active:cursor-grabbing"
          role="img"
          aria-label="Carte du monde des offres par lieu"
          onWheel={(e) => {
            const c = versSvg(e)
            zoomer(e.deltaY > 0 ? 1.2 : 1 / 1.2, c.x, c.y)
          }}
          onPointerDown={(e) => {
            glisse.current = { x: e.clientX, y: e.clientY, vx: vue.x, vy: vue.y, bouge: false }
            e.currentTarget.setPointerCapture(e.pointerId)
          }}
          onPointerMove={(e) => {
            const g = glisse.current
            if (!g) return
            const r = svg.current!.getBoundingClientRect()
            const dx = e.clientX - g.x
            const dy = e.clientY - g.y
            if (Math.abs(dx) + Math.abs(dy) > 3) g.bouge = true
            setVue((v) => ({ ...v, x: g.vx - (dx / r.width) * v.w, y: g.vy - (dy / r.height) * v.h }))
          }}
          onPointerUp={() => setTimeout(() => (glisse.current = null))}
        >
          <image href="/monde-clair.svg" width={L} height={H} className="dark:hidden" />
          <image href="/monde-sombre.svg" width={L} height={H} className="hidden dark:inline" />
          {tries.map((p) => {
            const { x, y } = projeter(p.lat, p.lon)
            const r = (8 + 26 * Math.sqrt(p.total / max)) * Math.max(0.35, echelle)
            const actif = choisi?.lieu === p.lieu
            return (
              <g
                key={p.lieu}
                role="button"
                tabIndex={0}
                aria-label={`${p.lieu} : ${p.total} offres, dont ${p.urgentes} urgentes`}
                className="cursor-pointer outline-none [&:focus-visible>circle:last-child]:stroke-ring"
                onClick={() => !glisse.current?.bouge && setChoisi(p)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setChoisi(p)}
              >
                {pressants.has(p.lieu) && <circle cx={x} cy={y} r={r} className="onde fill-urgent/40" />}
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  strokeWidth={2 * Math.max(0.35, echelle)}
                  className={cn(
                    "stroke-card transition-[fill] duration-200",
                    actif ? "fill-primary" : p.urgentes > 0 ? "fill-ambre/80 hover:fill-ambre" : "fill-ambre/45 hover:fill-ambre/70",
                  )}
                />
              </g>
            )
          })}
        </svg>
        <div className="absolute top-3 right-3 flex flex-col gap-1.5">
          <Button size="icon" variant="secondary" aria-label="Zoomer" onClick={() => zoomer(0.6)}>
            <PlusIcon />
          </Button>
          <Button size="icon" variant="secondary" aria-label="Dézoomer" onClick={() => zoomer(1 / 0.6)}>
            <MinusIcon />
          </Button>
          <Button size="icon" variant="secondary" aria-label="Vue d'ensemble" onClick={() => setVue(VUE_INITIALE)}>
            <RotateCcwIcon />
          </Button>
        </div>
        <div className="absolute bottom-3 left-3 flex flex-wrap items-center gap-3 rounded-full verre-carte/90 px-3.5 py-1.5 text-xs text-muted-foreground backdrop-blur">
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-ambre" /> Taille : nombre d&apos;offres
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-urgent/60" /> Halo : offres qui ferment sous 7 jours
          </span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {choisi ? (
          <motion.aside
            key={choisi.lieu}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 16 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
            className="flex flex-col rounded-[26px] verre-carte p-5 "
            aria-live="polite"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xl font-normal">{choisi.lieu}</h3>
              <Button size="icon-sm" variant="ghost" aria-label="Fermer" onClick={() => setChoisi(null)}>
                <XIcon />
              </Button>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[
                { n: choisi.total, l: "offres" },
                { n: choisi.marches, l: "marchés" },
                { n: choisi.emplois, l: "postes" },
              ].map(({ n, l }) => (
                <div key={l} className="rounded-2xl bg-muted py-3">
                  <p className="text-2xl font-light tabular-nums">{fr.format(n)}</p>
                  <p className="text-xs text-muted-foreground">{l}</p>
                </div>
              ))}
            </div>
            {choisi.urgentes > 0 && (
              <p className="mt-3 flex items-center gap-2 text-sm text-urgent">
                <span className="size-2 rounded-full bg-urgent battement" /> {fr.format(choisi.urgentes)} ferment sous 7 jours
              </p>
            )}
            {!!choisi.exemples?.length && (
              <ul className="mt-4 grid gap-1 text-sm">
                {choisi.exemples.slice(0, 5).map((o) => (
                  <li key={o.id}>
                    <Link href={lienOffre(o.id)} className="line-clamp-2 rounded-xl px-2 py-1.5 hover:bg-muted">
                      {o.titre}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <Button
              nativeButton={false}
              size="lg"
              className="mt-auto pt-0"
              render={<Link href={connecte ? lienOffres(choisi.lieu) : "/inscription"} />}
            >
              {connecte ? `Voir les ${fr.format(choisi.total)} offres` : "Créer un compte pour les voir"} <ArrowRightIcon />
            </Button>
          </motion.aside>
        ) : (
          <motion.aside
            key="aide"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="rounded-[26px] verre-carte p-5 "
          >
            <h3 className="font-medium">Lieux les plus actifs</h3>
            <p className="mt-1 text-sm text-muted-foreground">Cliquez sur un point ou un lieu pour voir ses offres.</p>
            <ol className="mt-4 grid gap-1">
              {tries.slice(0, 8).map((p) => (
                <li key={p.lieu}>
                  <button
                    type="button"
                    onClick={() => setChoisi(p)}
                    className="flex w-full items-center justify-between gap-3 rounded-xl px-2.5 py-2 text-left text-sm hover:bg-muted"
                  >
                    <span className="truncate">{p.lieu}</span>
                    <span className="text-muted-foreground tabular-nums">{fr.format(p.total)}</span>
                  </button>
                </li>
              ))}
            </ol>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  )
}
