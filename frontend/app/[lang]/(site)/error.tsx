"use client"

import { RotateCcwIcon } from "lucide-react"

import { Panneau } from "@/components/app/panneau"
import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"

/** Une erreur du serveur ou de l'API : on dit quoi faire, sans jargon. */
export default function Erreur({ reset }: { error: Error; reset: () => void }) {
  const d = useDico()
  return (
    <Panneau className="grid justify-items-center gap-4 py-16 text-center">
      <p className="text-2xl font-light">{d.erreurs.pageTitre}</p>
      <p className="max-w-md text-sm text-muted-foreground">{d.erreurs.pageTexte}</p>
      <Button onClick={reset} size="lg">
        <RotateCcwIcon /> {d.commun.reessayer}
      </Button>
    </Panneau>
  )
}
