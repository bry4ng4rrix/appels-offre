import Link from "next/link"

import { MarqueAO } from "@/components/app/marque"

export default function Introuvable() {
  return (
    <main className="m-3 grid flex-1 place-items-center rounded-[34px] bg-panneau p-8 text-center sm:m-4">
      <div className="grid justify-items-center gap-5">
        <MarqueAO className="size-14" />
        <p className="text-7xl font-light">404</p>
        <p className="max-w-sm text-muted-foreground">Cette page n&apos;existe pas, ou l&apos;offre a été retirée de la base.</p>
        <Link href="/offres" className="rounded-full bg-primary px-5 py-2.5 text-sm text-primary-foreground">
          Retour aux offres
        </Link>
      </div>
    </main>
  )
}
