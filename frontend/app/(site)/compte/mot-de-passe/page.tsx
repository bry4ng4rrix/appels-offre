import type { Metadata } from "next"

import { FormulaireMotDePasse } from "@/components/app/mot-de-passe"
import { Panneau } from "@/components/app/coque"
import { EnTetePage } from "@/components/app/page"

export const metadata: Metadata = { title: "Changer le mot de passe" }

export default function PageMotDePasse() {
  return (
    <Panneau>
      <EnTetePage titre="Changer de mot de passe">Changez le mot de passe de votre compte.</EnTetePage>
      <div className="mt-8">
        <FormulaireMotDePasse />
      </div>
    </Panneau>
  )
}
