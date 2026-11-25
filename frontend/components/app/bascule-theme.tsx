"use client"

import { AnimatePresence, motion } from "motion/react"
import { MoonIcon, SunIcon } from "lucide-react"
import { useTheme } from "next-themes"
import { useSyncExternalStore } from "react"

/** Clair ou sombre, dans la barre du haut. L'icone montre le theme vers lequel on bascule. */
export function BasculeTheme() {
  const { resolvedTheme, setTheme } = useTheme()
  // Le theme n'est connu qu'au navigateur : rien d'affirme pendant le rendu serveur.
  const monte = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )
  const sombre = monte && resolvedTheme === "dark"
  return (
    <button
      type="button"
      onClick={() => setTheme(sombre ? "light" : "dark")}
      aria-label={sombre ? "Passer au thème clair" : "Passer au thème sombre"}
      title={sombre ? "Thème clair" : "Thème sombre"}
      className="verre-carte grid size-10 place-items-center overflow-hidden rounded-full text-muted-foreground transition-colors hover:text-foreground"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={sombre ? "soleil" : "lune"}
          initial={{ rotate: -90, opacity: 0, scale: 0.6 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          exit={{ rotate: 90, opacity: 0, scale: 0.6 }}
          transition={{ duration: 0.2 }}
          className="grid place-items-center"
        >
          {sombre ? <SunIcon className="size-[18px]" /> : <MoonIcon className="size-[18px]" />}
        </motion.span>
      </AnimatePresence>
    </button>
  )
}
