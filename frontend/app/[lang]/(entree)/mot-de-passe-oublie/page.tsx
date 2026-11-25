
import { FormulaireOubli } from "@/components/entree/formulaires"
import { titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("oubli")

export default function PageOubli() {
  return <FormulaireOubli />
}
