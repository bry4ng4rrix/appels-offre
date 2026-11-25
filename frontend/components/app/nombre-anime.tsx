"use client"

import { animate, useReducedMotion } from "motion/react"
import { useEffect, useRef } from "react"

const fr = new Intl.NumberFormat("fr-FR")

/** Un nombre qui roule vers sa nouvelle valeur (credits debites, compteurs).
 *  Le serveur ecrit deja la valeur finale : sans JS, rien ne manque. */
export function NombreAnime({ valeur, depuisZero = false, duree = 0.6 }: { valeur: number; depuisZero?: boolean; duree?: number }) {
  const noeud = useRef<HTMLSpanElement>(null)
  const precedent = useRef(depuisZero ? 0 : valeur)
  const reduit = useReducedMotion()

  useEffect(() => {
    const el = noeud.current
    if (!el) return
    const depart = precedent.current
    precedent.current = valeur
    if (reduit || depart === valeur) {
      el.textContent = fr.format(valeur)
      return
    }
    const controle = animate(depart, valeur, {
      duration: duree,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => (el.textContent = fr.format(Math.round(v))),
    })
    return () => controle.stop()
  }, [valeur, reduit, duree])

  return (
    <span ref={noeud} className="tabular-nums">
      {fr.format(valeur)}
    </span>
  )
}
