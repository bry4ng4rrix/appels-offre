"use client"

import { startTransition, useActionState, useEffect, useRef } from "react"
import { toast } from "sonner"

import type { Resultat } from "@/lib/api/types"

type Action = (precedent: Resultat | null, f: FormData) => Promise<Resultat>

/** Envoi sans `<form action>` : React 19 viderait les champs apres chaque envoi, et une
 *  erreur ferait perdre la saisie. Ici les champs gardent ce que la personne a tape. */
export function useEnvoi(action: Action) {
  const [etat, soumettre, enCours] = useActionState(action, null)
  const surEnvoi = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const donnees = new FormData(e.currentTarget)
    startTransition(() => soumettre(donnees))
  }
  return { etat, surEnvoi, enCours, erreurs: etat && !etat.ok ? etat.champs : undefined }
}

/** useEnvoi + toast : chaque formulaire annonce son resultat de la meme facon. */
export function useFormulaire(action: Action) {
  const envoi = useEnvoi(action)
  const vu = useRef<Resultat | null>(null)
  useEffect(() => {
    const etat = envoi.etat
    if (!etat || etat === vu.current) return
    vu.current = etat
    if (etat.ok) toast.success(etat.message ?? "Enregistré.")
    else toast.error(etat.erreur)
  }, [envoi.etat])
  return envoi
}
