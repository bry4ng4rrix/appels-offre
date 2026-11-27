import { BookOpenCheckIcon, CircleCheckIcon, FlagIcon, GlobeIcon, LayersIcon, RotateCcwIcon, SparklesIcon } from "lucide-react"
import type { Metadata } from "next"
import { Suspense } from "react"

import { CartePlan } from "@/components/abonnement/carte-plan"
import { BoutonLien } from "@/components/app/bouton-lien"
import { Panneau } from "@/components/app/coque"
import { NombreAnime } from "@/components/app/nombre-anime"
import { GrilleOffres } from "@/components/offres/carte-offre"
import { CarteHero } from "@/components/vitrine/carte-hero"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Skeleton } from "@/components/ui/skeleton"
import { formateurs } from "@/lib/format"
import { f } from "@/lib/i18n"
import { dico } from "@/lib/i18n/serveur"
import { pointsPublics, vitrine } from "@/lib/public"
import { moiOuRien, plans } from "@/lib/session"

export async function generateMetadata(): Promise<Metadata> {
  return { title: { absolute: (await dico()).titres.accueilComplet } }
}

export default function Accueil() {
  return (
    <div className="grid gap-4">
      <Suspense fallback={<Skeleton className="h-[34rem] w-full rounded-[30px]" />}>
        <Hero />
      </Suspense>
      <Suspense fallback={<Skeleton className="h-[40rem] w-full rounded-[30px]" />}>
        <Urgentes />
      </Suspense>
      <Suspense fallback={null}>
        <Questions />
      </Suspense>
      <Suspense fallback={null}>
        <Credits />
      </Suspense>
      <Suspense fallback={null}>
        <Appel />
      </Suspense>
    </div>
  )
}

function Tuile({ icone, libelle, valeur }: { icone: React.ReactNode; libelle: string; valeur: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col justify-between gap-1 rounded-2xl verre-carte px-3 py-3 sm:px-4">
      <p className="flex items-start gap-1.5 text-xs leading-tight text-muted-foreground [&>svg]:mt-px [&>svg]:shrink-0">
        {icone}
        {libelle}
      </p>
      <p className="text-2xl font-light tabular-nums">{valeur}</p>
    </div>
  )
}

async function Boutons() {
  const [m, d] = await Promise.all([moiOuRien(), dico()])
  if (m)
    return (
      <BoutonLien href={m.admin ? "/offres" : "/pour-vous"} size="lg" className="h-12 px-6 text-base">
        <SparklesIcon /> {m.admin ? d.vitrine.voirOffres : d.vitrine.voirSuggestions}
      </BoutonLien>
    )
  return (
    <>
      <BoutonLien href="/inscription" size="lg" className="h-12 px-6 text-base">
        {d.vitrine.creerGratuit}
      </BoutonLien>
      <BoutonLien href="/connexion" variant="secondary" size="lg" className="h-12 px-6 text-base">
        {d.nav.seConnecter}
      </BoutonLien>
    </>
  )
}

async function Hero() {
  const [{ stats, nbSources }, points, d] = await Promise.all([vitrine(), pointsPublics(), dico()])
  const { entier } = formateurs(d.locale)
  return (
    <Panneau className="grid items-center gap-8 lg:grid-cols-[1.25fr_1fr] lg:p-10">
      <div>
        <span className="inline-flex items-center gap-2 rounded-full bg-accent px-3 py-1 text-xs text-accent-foreground">
          <span className="size-1.5 rounded-full bg-ambre battement" /> {d.vitrine.collecte}
        </span>
        <h2 className="mt-5 text-4xl leading-[1.1] font-light tracking-tight text-balance sm:text-5xl">
          {d.vitrine.titre}
        </h2>
        <p className="mt-5 max-w-xl leading-relaxed text-muted-foreground">
          {d.vitrine.texte}
        </p>
        <div className="mt-7 grid grid-cols-3 gap-2">
          <Tuile icone={<LayersIcon className="size-3.5" />} libelle={d.vitrine.ouvertes} valeur={<NombreAnime valeur={stats.ouvertes} depuisZero duree={1.2} />} />
          <Tuile icone={<FlagIcon className="size-3.5 text-urgent" />} libelle={d.vitrine.sous7} valeur={<NombreAnime valeur={stats.urgentes} depuisZero duree={1.2} />} />
          <Tuile icone={<GlobeIcon className="size-3.5" />} libelle={d.vitrine.sources} valeur={entier(nbSources)} />
        </div>
        <div className="mt-7 flex flex-wrap gap-2 max-sm:*:grow">
          <Suspense fallback={<Skeleton className="h-12 w-56 rounded-full" />}>
            <Boutons />
          </Suspense>
        </div>
      </div>
      <CarteHero points={points} libelle={d.carteMonde.heroLien} legende={d.carteMonde.heroLegende} />
    </Panneau>
  )
}

async function Urgentes() {
  const [{ urgentes, stats }, d] = await Promise.all([vitrine(), dico()])
  const { entier } = formateurs(d.locale)
  return (
    <Panneau>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2.5 text-xl font-medium sm:text-[1.4rem]">
            <span className="size-2.5 rounded-full bg-urgent" aria-hidden /> {d.vitrine.urgentesTitre}
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {f(d.vitrine.urgentesTexte, { n: entier(stats.urgentes) })}
          </p>
        </div>
        <BoutonLien href="/offres?etat=actionnables" variant="secondary" size="lg" className="max-sm:w-full">
          {d.vitrine.toutes}
        </BoutonLien>
      </div>
      <div className="mt-6">
        {urgentes.length ? (
          <GrilleOffres offres={urgentes} />
        ) : (
          <p className="rounded-[22px] bg-card p-10 text-center text-muted-foreground">{d.vitrine.aucuneUrgente}</p>
        )}
      </div>
    </Panneau>
  )
}

async function Questions() {
  const [{ stats, nbSources }, d] = await Promise.all([vitrine(), dico()])
  const { entier } = formateurs(d.locale)
  const faq = [
    { q: d.vitrine.q1, r: f(d.vitrine.r1, { sources: nbSources, total: entier(stats.retenues) }) },
    { q: d.vitrine.q2, r: d.vitrine.r2 },
    { q: d.vitrine.q3, r: d.vitrine.r3 },
  ]
  return (
    <Panneau className="grid gap-6 lg:grid-cols-[18rem_1fr]">
      <div id="questions" className="scroll-mt-24">
        <h2 className="text-xl font-medium sm:text-[1.4rem]">{d.vitrine.faqTitre}</h2>
        <p className="mt-1.5 text-sm text-muted-foreground">{d.vitrine.faqTexte}</p>
      </div>
      <Accordion defaultValue={[faq[0].q]} className="grid gap-2">
        {faq.map((f) => (
          <AccordionItem key={f.q} value={f.q} className="rounded-[22px] border-0 verre-carte px-5 ">
            <AccordionTrigger className="text-base font-normal hover:no-underline">{f.q}</AccordionTrigger>
            <AccordionContent className="text-muted-foreground">{f.r}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </Panneau>
  )
}

async function Credits() {
  const [liste, d] = await Promise.all([plans(), dico()])
  const etapes = [
    { icone: BookOpenCheckIcon, titre: d.vitrine.c1Titre, texte: d.vitrine.c1Texte },
    { icone: CircleCheckIcon, titre: d.vitrine.c2Titre, texte: d.vitrine.c2Texte },
    { icone: RotateCcwIcon, titre: d.vitrine.c3Titre, texte: d.vitrine.c3Texte },
  ]
  return (
    <Panneau>
      <h2 className="text-xl font-medium sm:text-[1.4rem]">{d.vitrine.creditsTitre}</h2>
      <p className="mt-1.5 text-sm text-muted-foreground">
        {d.vitrine.creditsTexte}
      </p>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        {etapes.map(({ icone: Icone, titre, texte }) => (
          <div key={titre} className="rounded-[22px] verre-carte p-5 ">
            <span className="grid size-10 place-items-center rounded-full bg-ambre text-ambre-foreground">
              <Icone className="size-5" />
            </span>
            <h3 className="mt-4 font-medium">{titre}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{texte}</p>
          </div>
        ))}
      </div>
      {liste.length > 0 && (
        <>
          <h3 className="mt-10 text-lg font-medium">{d.vitrine.plusCredits}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{d.vitrine.plusCreditsTexte}</p>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {liste.map((p, i) => (
              <CartePlan
                key={p.id}
                plan={p}
                vedette={i === 1}
                action={
                  <BoutonLien href="/abonnement" variant={i === 1 ? "default" : "secondary"} size="lg" className="h-11 w-full">
                    {d.plan.choisirCe}
                  </BoutonLien>
                }
              />
            ))}
          </div>
        </>
      )}
    </Panneau>
  )
}

async function Appel() {
  const [m, { stats }, d] = await Promise.all([moiOuRien(), vitrine(), dico()])
  const { entier } = formateurs(d.locale)
  if (m) return null
  return (
    <section className="flex flex-wrap items-center justify-between gap-6 rounded-[30px] bg-primary p-6 text-primary-foreground sm:p-10">
      <p className="max-w-xl text-2xl font-light text-balance sm:text-3xl">
        {f(d.vitrine.appel, { n: entier(stats.ouvertes) })}
      </p>
      <div className="flex flex-wrap gap-2 max-sm:w-full max-sm:*:grow">
        <BoutonLien href="/inscription" variant="secondary" size="lg" className="h-12 px-6">
          {d.nav.creerCompte}
        </BoutonLien>
        <BoutonLien href="/connexion" variant="ghost" size="lg" className="h-12 px-6 text-primary-foreground hover:bg-white/10 hover:text-primary-foreground">
          {d.nav.seConnecter}
        </BoutonLien>
      </div>
    </section>
  )
}
