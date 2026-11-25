"use client"

import { RotateCcwIcon } from "lucide-react"

import { Panneau } from "@/components/app/panneau"
import { Button } from "@/components/ui/button"

/** Une erreur du serveur ou de l'API : on dit quoi faire, sans jargon. */
export default function Erreur({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panneau className="grid justify-items-center gap-4 py-16 text-center">
      <p className="text-2xl font-light">Le serveur n&apos;a pas pu répondre.</p>
      <p className="max-w-md text-sm text-muted-foreground">
        La connexion à l&apos;API a échoué ou a pris trop de temps. Réessayez dans un instant ; si cela dure, prévenez
        l&apos;administrateur.
      </p>
      <Button onClick={reset} size="lg">
        <RotateCcwIcon /> Réessayer
      </Button>
    </Panneau>
  )
}
