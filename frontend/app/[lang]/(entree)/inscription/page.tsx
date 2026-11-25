import type { Metadata } from "next"

import { FormulaireInscription } from "@/components/entree/formulaires"

export const metadata: Metadata = { title: "Créer un compte" }

export default function PageInscription() {
  return <FormulaireInscription />
}
