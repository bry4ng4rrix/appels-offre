
import { FormulaireInscription } from "@/components/entree/formulaires"
import { titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("inscription")

export default function PageInscription() {
  return <FormulaireInscription />
}
