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
import { entier } from "@/lib/format"
import { pointsPublics, vitrine } from "@/lib/public"
import { moiOuRien, plans } from "@/lib/session"

export const metadata: Metadata = {
  title: { absolute: "Appels d'offres internationaux qui clôturent cette semaine · Label Collectes" },
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
    <div className="rounded-2xl verre-carte px-4 py-3 ">
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icone}
        {libelle}
      </p>
      <p className="mt-1 text-2xl font-light">{valeur}</p>
    </div>
  )
}

async function Boutons() {
  const m = await moiOuRien()
  if (m)
    return (
      <BoutonLien href={m.admin ? "/offres" : "/pour-vous"} size="lg" className="h-12 px-6 text-base">
        <SparklesIcon /> {m.admin ? "Voir les offres" : "Voir mes suggestions"}
      </BoutonLien>
    )
  return (
    <>
      <BoutonLien href="/inscription" size="lg" className="h-12 px-6 text-base">
        Créer un compte gratuit
      </BoutonLien>
      <BoutonLien href="/connexion" variant="secondary" size="lg" className="h-12 px-6 text-base">
        Se connecter
      </BoutonLien>
    </>
  )
}

async function Hero() {
  const [{ stats, nbSources }, points] = await Promise.all([vitrine(), pointsPublics()])
  return (
    <Panneau className="grid items-center gap-8 lg:grid-cols-[1.25fr_1fr] lg:p-10">
      <div>
        <span className="inline-flex items-center gap-2 rounded-full bg-accent px-3 py-1 text-xs text-accent-foreground">
          <span className="size-1.5 rounded-full bg-ambre battement" /> Collecte toutes les 6 heures
        </span>
        <h2 className="mt-5 text-4xl leading-[1.1] font-light tracking-tight text-balance sm:text-5xl">
          Trouvez les appels d&apos;offres qui vous correspondent, avant leur date limite.
        </h2>
        <p className="mt-5 max-w-xl leading-relaxed text-muted-foreground">
          Les appels d&apos;offres et offres d&apos;emploi des bailleurs, des Nations unies, des ONG et des marchés publics, pour les
          entreprises, les consultants et les candidats qui y répondent.
        </p>
        <div className="mt-7 grid grid-cols-3 gap-2">
          <Tuile icone={<LayersIcon className="size-3.5" />} libelle="Ouvertes" valeur={<NombreAnime valeur={stats.ouvertes} depuisZero duree={1.2} />} />
          <Tuile icone={<FlagIcon className="size-3.5 text-urgent" />} libelle="Sous 7 jours" valeur={<NombreAnime valeur={stats.urgentes} depuisZero duree={1.2} />} />
          <Tuile icone={<GlobeIcon className="size-3.5" />} libelle="Sources" valeur={entier(nbSources)} />
        </div>
        <div className="mt-7 flex flex-wrap gap-2">
          <Suspense fallback={<Skeleton className="h-12 w-56 rounded-full" />}>
            <Boutons />
          </Suspense>
        </div>
      </div>
      <CarteHero points={points} />
    </Panneau>
  )
}

async function Urgentes() {
  const { urgentes, stats } = await vitrine()
  return (
    <Panneau>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2.5 text-xl font-medium sm:text-[1.4rem]">
            <span className="size-2.5 rounded-full bg-urgent" aria-hidden /> Clôture sous 7 jours
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {entier(stats.urgentes)} offres ferment cette semaine. Voici les plus proches de leur date limite.
          </p>
        </div>
        <BoutonLien href="/offres?etat=actionnables" variant="secondary" size="lg">
          Toutes les offres
        </BoutonLien>
      </div>
      <div className="mt-6">
        {urgentes.length ? (
          <GrilleOffres offres={urgentes} />
        ) : (
          <p className="rounded-[22px] bg-card p-10 text-center text-muted-foreground">Aucune offre ne ferme dans les 7 prochains jours.</p>
        )}
      </div>
    </Panneau>
  )
}

async function Questions() {
  const { stats, nbSources } = await vitrine()
  const faq = [
    {
      q: "Qu'est-ce que Label Collectes ?",
      r: `Une veille des appels d'offres et des offres d'emploi publiés par ${nbSources} sources : bailleurs, agences des Nations unies, ONG et portails nationaux de marchés publics. ${entier(stats.retenues)} offres collectées à ce jour, triées par secteur, pays et date limite.`,
    },
    {
      q: "Quelles offres sont affichées ici ?",
      r: "Celles qui clôturent dans les 7 prochains jours, de la plus proche à la plus lointaine. La carte montre toutes les offres ouvertes par lieu.",
    },
    {
      q: "Comment accéder aux annonces officielles ?",
      r: "Créez un compte gratuit : vous ouvrez jusqu'à 10 annonces officielles par jour, la liste complète avec ses filtres, des suggestions selon votre profil et des alertes par email. Un abonnement ajoute des crédits.",
    },
  ]
  return (
    <Panneau className="grid gap-6 lg:grid-cols-[18rem_1fr]">
      <div id="questions" className="scroll-mt-24">
        <h2 className="text-xl font-medium sm:text-[1.4rem]">Questions fréquentes</h2>
        <p className="mt-1.5 text-sm text-muted-foreground">Ce qu&apos;il faut savoir avant de commencer.</p>
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
  const liste = await plans()
  const etapes = [
    { icone: BookOpenCheckIcon, titre: "10 crédits offerts chaque jour", texte: "Avec un compte gratuit. Le compteur repart chaque matin." },
    { icone: CircleCheckIcon, titre: "Un crédit par annonce ouverte", texte: "Il est décompté au clic sur « Consulter l'annonce officielle »." },
    { icone: RotateCcwIcon, titre: "Rouvrir ne coûte rien", texte: "La même offre, rouverte le même jour, ne compte qu'une fois." },
  ]
  return (
    <Panneau>
      <h2 className="text-xl font-medium sm:text-[1.4rem]">Crédits et abonnements</h2>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Chercher, filtrer et lire les fiches est gratuit. Les crédits servent à ouvrir les annonces officielles.
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
          <h3 className="mt-10 text-lg font-medium">Besoin de plus de crédits ?</h3>
          <p className="mt-1 text-sm text-muted-foreground">Pas de paiement en ligne : l&apos;abonnement est activé dès réception de votre règlement.</p>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {liste.map((p, i) => (
              <CartePlan
                key={p.id}
                plan={p}
                gratuits={10}
                vedette={i === 1}
                action={
                  <BoutonLien href="/abonnement" variant={i === 1 ? "default" : "secondary"} size="lg" className="h-11 w-full">
                    Choisir ce plan
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
  const [m, { stats }] = await Promise.all([moiOuRien(), vitrine()])
  if (m) return null
  return (
    <section className="flex flex-wrap items-center justify-between gap-6 rounded-[30px] bg-primary p-8 text-primary-foreground sm:p-10">
      <p className="max-w-xl text-2xl font-light text-balance sm:text-3xl">
        Connectez-vous pour voir les {entier(stats.ouvertes)} offres disponibles, avec leurs annonces officielles.
      </p>
      <div className="flex flex-wrap gap-2">
        <BoutonLien href="/inscription" variant="secondary" size="lg" className="h-12 px-6">
          Créer un compte
        </BoutonLien>
        <BoutonLien href="/connexion" variant="ghost" size="lg" className="h-12 px-6 text-primary-foreground hover:bg-white/10 hover:text-primary-foreground">
          Se connecter
        </BoutonLien>
      </div>
    </section>
  )
}
