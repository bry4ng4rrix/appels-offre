import { BellIcon, CircleHelpIcon } from "lucide-react"
import Link from "next/link"
import { Suspense } from "react"

import { BasculeTheme } from "@/components/app/bascule-theme"
import { ChoixLangue } from "@/components/app/choix-langue"
import { BoutonLien } from "@/components/app/bouton-lien"
import { PastilleCredits } from "@/components/app/credits"
import { LogoLabel, MarqueAO } from "@/components/app/marque"
import { MenuCompte } from "@/components/app/menu-compte"
import { BarreMobile, Rail, TitrePage, type LienNav } from "@/components/app/rail"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { Moi, PageAbonnementsAdmin } from "@/lib/api/types"
import type { Dico } from "@/lib/i18n"
import { dico } from "@/lib/i18n/serveur"
import { moiOuRien } from "@/lib/session"

async function liensDe(m: Moi | null, d: Dico): Promise<{ liens: LienNav[]; reglages?: LienNav }> {
  if (!m)
    return {
      liens: [
        { href: "/", libelle: d.titres.accueil, icone: "accueil" },
        { href: "/carte", libelle: d.nav.carte, icone: "carte" },
      ],
    }
  if (!m.admin)
    return {
      liens: [
        { href: "/pour-vous", libelle: d.titres.pourVous, icone: "pourvous" },
        { href: "/offres", libelle: d.titres.offres, icone: "offres" },
        { href: "/carte", libelle: d.nav.carte, icone: "carte" },
        { href: "/abonnement", libelle: d.titres.abonnement, icone: "abonnement" },
        { href: "/notifications", libelle: d.titres.notifications, icone: "notifications" },
      ],
      reglages: { href: "/profil", libelle: d.titres.profil, icone: "parametres" },
    }
  const attente = await api<PageAbonnementsAdmin>("/api/v1/admin/abonnements/", { query: { statut: "attente", par_page: 1 } })
    .then((p) => p.en_attente)
    .catch(() => 0)
  return {
    liens: [
      { href: "/offres", libelle: d.titres.offres, icone: "offres" },
      { href: "/carte", libelle: d.nav.carte, icone: "carte" },
      { href: "/admin/taches", libelle: d.titres.taches, icone: "taches" },
      { href: "/admin/abonnements", libelle: d.titres.abonnements, icone: "abonnements", pastille: attente },
    ],
    reglages: { href: "/admin/parametres", libelle: d.titres.parametres, icone: "parametres" },
  }
}

async function Navigation({ mobile = false }: { mobile?: boolean }) {
  const { liens, reglages } = await liensDe(await moiOuRien(), await dico())
  return mobile ? <BarreMobile liens={reglages ? [...liens.slice(0, 4), reglages] : liens} /> : <Rail liens={liens} reglages={reglages} />
}

const ROND = "verre-carte grid size-10 place-items-center rounded-full text-muted-foreground transition-colors hover:text-foreground"

async function Compte() {
  const [m, d] = await Promise.all([moiOuRien(), dico()])
  if (!m)
    return (
      <>
        <ChoixLangue />
        <BasculeTheme />
        <BoutonLien href="/connexion" variant="secondary" size="lg" className="hidden sm:inline-flex">
          {d.nav.seConnecter}
        </BoutonLien>
        <BoutonLien href="/inscription" size="lg">
          {d.nav.creerCompte}
        </BoutonLien>
      </>
    )
  const nom = [m.prenom, m.nom].filter(Boolean).join(" ")
  return (
    <>
      {!m.admin && <PastilleCredits credits={m.credits} />}
      <ChoixLangue />
      <BasculeTheme />
      <Link href="/#questions" aria-label={d.nav.aide} className={`${ROND} hidden sm:grid`}>
        <CircleHelpIcon className="size-[18px]" />
      </Link>
      {/* Sur telephone, les notifications sont dans la barre du bas et le menu du compte. */}
      <Link href="/notifications" aria-label={d.nav.mesNotifications} className={`${ROND} hidden sm:grid`}>
        <BellIcon className="size-[18px]" />
      </Link>
      <MenuCompte email={m.email} nom={nom} admin={m.admin} photo={!!m.avatar} />
    </>
  )
}

/** Le cadre de l'app : rail a gauche, barre du haut, contenu ; barre flottante sur telephone. */
export async function Coque({ children }: { children: React.ReactNode }) {
  const d = await dico()
  return (
    <div className="mx-auto flex w-full max-w-[1640px] flex-1 gap-4 p-3 pb-24 sm:p-4 md:pb-4">
      <Suspense fallback={<div className="sticky top-4 hidden h-[calc(100dvh-2rem)] w-[72px] shrink-0 verre rounded-[36px] md:block" />}>
        <Navigation />
      </Suspense>
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <header className="flex h-[68px] shrink-0 items-center gap-2.5 verre rounded-[34px] pe-3 ps-3 sm:gap-3 sm:ps-7">
          <Link href="/" aria-label={d.nav.accueilLien} className="md:hidden">
            <MarqueAO />
          </Link>
          <Suspense fallback={<span className="h-8 w-40" />}>
            <TitrePage />
          </Suspense>
          <div className="ms-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
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
            <span className="max-w-56">{d.nav.pied}</span>
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
