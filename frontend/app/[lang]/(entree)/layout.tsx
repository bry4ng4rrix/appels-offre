import Link from "next/link"

import { MarqueAO } from "@/components/app/marque"
import { ChiffresEntree } from "@/components/entree/chiffres"
import { IllustrationEquipe } from "@/components/entree/illustration-equipe"

/** Connexion et inscription : l'illustration a gauche, le formulaire a droite (dessus sur mobile). */
export default function LayoutEntree({ children }: LayoutProps<"/">) {
  return (
    <div className="mx-auto grid min-h-dvh w-full max-w-[1500px] gap-4 p-3 sm:p-4 lg:grid-cols-[1.1fr_1fr]">
      <aside className="order-2 flex flex-col verre rounded-[34px] p-8 sm:p-10 lg:order-1">
        <Link href="/" className="flex items-center gap-3" aria-label="Label Collectes, accueil">
          <MarqueAO className="size-11" />
          <span className="text-lg font-medium">Label Collectes</span>
        </Link>
        <h2 className="mt-10 max-w-md text-3xl leading-tight font-light tracking-tight text-balance sm:text-4xl">
          Les appels d&apos;offres et les offres d&apos;emploi, triés selon votre profil.
        </h2>
        <div className="flex flex-1 items-center justify-center py-8">
          <IllustrationEquipe className="block h-auto w-full max-w-xl" />
        </div>
        <ChiffresEntree />
      </aside>
      <main className="verre order-1 flex flex-col rounded-[34px] px-5 py-8 sm:px-10 lg:order-2">
        <Link href="/" className="flex items-center gap-2.5 lg:hidden" aria-label="Label Collectes, accueil">
          <MarqueAO />
          <span className="font-medium">Label Collectes</span>
        </Link>
        <div className="mx-auto my-auto w-full max-w-sm py-10">{children}</div>
      </main>
    </div>
  )
}
