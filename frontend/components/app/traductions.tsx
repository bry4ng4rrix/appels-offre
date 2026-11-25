"use client"

import { createContext, use } from "react"

import { DICOS, type Dico } from "@/lib/i18n"
import type { Langue } from "@/lib/i18n/langues"

const Contexte = createContext<Langue>("fr")

/** La langue de la page, pour les composants client (le dictionnaire est dans le bundle). */
export function Traductions({ langue, children }: { langue: Langue; children: React.ReactNode }) {
  return <Contexte value={langue}>{children}</Contexte>
}

export function useLangue(): Langue {
  return use(Contexte)
}

export function useDico(): Dico {
  return DICOS[use(Contexte)]
}
