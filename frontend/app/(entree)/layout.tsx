import Link from "next/link"

import { Tuile } from "@/components/app/marque"
import { ChiffresEntree } from "@/components/entree/chiffres"

/** Connexion et inscription : le formulaire a droite, la promesse du service a gauche. */
export default function LayoutEntree({ children }: LayoutProps<"/">) {
  return (
    <div className="mx-auto grid min-h-dvh w-full max-w-[1500px] gap-4 p-3 sm:p-4 lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden rounded-[34px] bg-primary p-10 text-primary-foreground lg:flex lg:flex-col">
        <Link href="/" className="flex items-center gap-3" aria-label="Label Collectes, accueil">
          <Tuile className="size-12 rounded-full bg-white/10" />
          <span className="text-xl font-medium">Label Collectes</span>
        </Link>
        <div className="mt-auto max-w-lg">
          <p className="text-4xl leading-tight font-light tracking-tight text-balance">
            Les appels d&apos;offres des bailleurs, des Nations unies et des ONG, avant qu&apos;ils ne ferment.
          </p>
          <ChiffresEntree />
        </div>
        {/* La carte du monde, en filigrane : les offres viennent de partout. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-16 h-[55%] bg-[url(/monde-sombre.svg)] bg-contain bg-center bg-no-repeat opacity-60 dark:bg-[url(/monde-clair.svg)] dark:opacity-25"
        />
      </aside>
      <main className="flex flex-col rounded-[34px] bg-panneau px-5 py-8 sm:px-10">
        <Link href="/" className="flex items-center gap-2.5 lg:hidden" aria-label="Label Collectes, accueil">
          <Tuile className="size-10 rounded-full" />
          <span className="font-medium">Label Collectes</span>
        </Link>
        <div className="mx-auto my-auto w-full max-w-sm py-10">{children}</div>
      </main>
    </div>
  )
}
