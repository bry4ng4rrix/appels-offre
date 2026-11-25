
import { FormulaireMotDePasse } from "@/components/app/mot-de-passe"
import { Panneau } from "@/components/app/coque"
import { EnTetePage } from "@/components/app/page"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("changerMdp")

export default async function PageMotDePasse() {
  const d = await dico()
  return (
    <Panneau>
      <EnTetePage titre={d.mdp.sectionTitre}>{d.mdp.sectionTexte}</EnTetePage>
      <div className="mt-8">
        <FormulaireMotDePasse />
      </div>
    </Panneau>
  )
}
