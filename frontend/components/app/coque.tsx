import { BellIcon, CircleHelpIcon } from "lucide-react"
import Link from "next/link"
import { Suspense } from "react"

import { BasculeTheme } from "@/components/app/bascule-theme"
import { BoutonLien } from "@/components/app/bouton-lien"
import { PastilleCredits } from "@/components/app/credits"
import { LogoLabel, MarqueAO } from "@/components/app/marque"
import { MenuCompte } from "@/components/app/menu-compte"
import { BarreMobile, Rail, TitrePage, type LienNav } from "@/components/app/rail"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Moi, PageAbonnementsAdmin } from "@/lib/api/types"
import { moiOuRien } from "@/lib/session"

async function liensDe(m: Moi | null): Promise<{ liens: LienNav[]; reglages?: LienNav }> {
  if (!m)
    return {
      liens: [
        { href: "/", libelle: "Accueil", icone: "accueil" },
        { href: "/carte", libelle: "Carte", icone: "carte" },
      ],
    }
  if (!m.admin)
    return {
      liens: [
        { href: "/pour-vous", libelle: "Pour vous", icone: "pourvous" },
        { href: "/offres", libelle: "Offres", icone: "offres" },
        { href: "/carte", libelle: "Carte", icone: "carte" },
        { href: "/abonnement", libelle: "Abonnement", icone: "abonnement" },
        { href: "/notifications", libelle: "Notifications", icone: "notifications" },
      ],
      reglages: { href: "/profil", libelle: "Mon profil", icone: "parametres" },
    }
  const attente = await api<PageAbonnementsAdmin>("/api/v1/admin/abonnements/", { query: { statut: "attente", par_page: 1 } })
    .then((p) => p.en_attente)
    .catch(() => 0)
  return {
    liens: [
      { href: "/offres", libelle: "Offres", icone: "offres" },
      { href: "/carte", libelle: "Carte", icone: "carte" },
      { href: "/admin/taches", libelle: "Tâches", icone: "taches" },
      { href: "/admin/abonnements", libelle: "Abonnements", icone: "abonnements", pastille: attente },
    ],
    reglages: { href: "/admin/parametres", libelle: "Paramètres", icone: "parametres" },
  }
}

async function Navigation({ mobile = false }: { mobile?: boolean }) {
  const { liens, reglages } = await liensDe(await moiOuRien())
  return mobile ? <BarreMobile liens={reglages ? [...liens.slice(0, 4), reglages] : liens} /> : <Rail liens={liens} reglages={reglages} />
}

const ROND = "verre-carte grid size-10 place-items-center rounded-full text-muted-foreground transition-colors hover:text-foreground"

async function Compte() {
  const m = await moiOuRien()
  if (!m)
    return (
      <>
        <BasculeTheme />
        <BoutonLien href="/connexion" variant="secondary" size="lg" className="hidden sm:inline-flex">
          Se connecter
        </BoutonLien>
        <BoutonLien href="/inscription" size="lg">
          Créer un compte
        </BoutonLien>
      </>
    )
  const nom = [m.prenom, m.nom].filter(Boolean).join(" ")
  return (
    <>
      {!m.admin && <PastilleCredits credits={m.credits} />}
      <BasculeTheme />
      <Link href="/#questions" aria-label="Aide et questions fréquentes" className={`${ROND} hidden sm:grid`}>
        <CircleHelpIcon className="size-[18px]" />
      </Link>
      <Link href="/notifications" aria-label="Mes notifications" className={ROND}>
        <BellIcon className="size-[18px]" />
      </Link>
      <MenuCompte email={m.email} nom={nom} admin={m.admin} photo={!!m.avatar} />
    </>
  )
}

/** Le cadre de l'app : rail a gauche, barre du haut, contenu ; barre flottante sur telephone. */
export function Coque({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-[1640px] flex-1 gap-4 p-3 pb-24 sm:p-4 md:pb-4">
      <Suspense fallback={<div className="sticky top-4 hidden h-[calc(100dvh-2rem)] w-[72px] shrink-0 verre rounded-[36px] md:block" />}>
        <Navigation />
      </Suspense>
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="flex h-[68px] shrink-0 items-center gap-3 verre rounded-[34px] pr-3 pl-3 sm:pl-7">
          <Link href="/" aria-label="Accueil" className="md:hidden">
            <MarqueAO />
          </Link>
          <Suspense fallback={<span className="h-8 w-40" />}>
            <TitrePage />
          </Suspense>
          <div className="ml-auto flex items-center gap-2">
            <Suspense fallback={<Skeleton className="h-10 w-40 rounded-full" />}>
              <Compte />
            </Suspense>
          </div>
        </header>
        <main id="contenu" className="flex-1">
          {children}
        </main>
        <footer className="verre flex flex-wrap items-center justify-between gap-4 rounded-[26px] px-5 py-3 text-xs text-muted-foreground">
          <a href="https://labeltechnology.mg" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 hover:text-foreground">
            <LogoLabel />
            <span className="max-w-56">Label Collectes, la veille des appels d&apos;offres par Label Technology.</span>
          </a>
          <a href="mailto:contact@labeltechnology.mg" className="hover:text-foreground">
            contact@labeltechnology.mg
          </a>
        </footer>
      </div>
      <Suspense fallback={null}>
        <Navigation mobile />
      </Suspense>
    </div>
  )
}

export { Panneau } from "@/components/app/panneau"
