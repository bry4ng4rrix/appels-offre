"use client"

import { useActionState, useEffect, useRef } from "react"
import { toast } from "sonner"

import type { Resultat } from "@/lib/api/types"

type Action = (precedent: Resultat | null, f: FormData) => Promise<Resultat>

/** useActionState + toast : chaque formulaire annonce son resultat de la meme facon. */
export function useFormulaire(action: Action, { silencieux = false }: { silencieux?: boolean } = {}) {
  const [etat, soumettre, enCours] = useActionState(action, null)
  const vu = useRef<Resultat | null>(null)
  useEffect(() => {
    if (!etat || etat === vu.current || silencieux) return
    vu.current = etat
    if (etat.ok) toast.success(etat.message ?? "Enregistré.")
    else toast.error(etat.erreur)
  }, [etat, silencieux])
  return { etat, soumettre, enCours, erreurs: etat && !etat.ok ? etat.champs : undefined }
}
