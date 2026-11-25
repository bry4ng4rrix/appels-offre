import type { Metadata } from "next"

import { FormulaireOubli } from "@/components/entree/formulaires"

export const metadata: Metadata = { title: "Mot de passe oublié" }

export default function PageOubli() {
  return <FormulaireOubli />
}
