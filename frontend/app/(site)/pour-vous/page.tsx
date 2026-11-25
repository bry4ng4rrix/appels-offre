import { SlidersHorizontalIcon } from "lucide-react"
import type { Metadata } from "next"
import { Suspense } from "react"

import { Anneau } from "@/components/app/anneau"
import { BoutonLien } from "@/components/app/bouton-lien"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, GrilleSquelette, Pagination, Vide, aplatir } from "@/components/app/page"
import { GrilleOffres } from "@/components/offres/carte-offre"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { PageSuggestions } from "@/lib/api/types"
import { entier, pluriel } from "@/lib/format"
import { moi } from "@/lib/session"

export const metadata: Metadata = { title: "Pour vous" }

export default function PagePourVous({ searchParams }: PageProps<"/pour-vous">) {
  return (
    <Suspense
      fallback={
        <>
          <Skeleton className="h-16 w-64" />
          <Skeleton className="mt-8 h-24 w-full rounded-2xl" />
          <div className="mt-8">
            <GrilleSquelette />
          </div>
        </>
      }
    >
      <Suggestions searchParams={searchParams} />
    </Suspense>
  )
}

async function Suggestions({ searchParams }: Pick<PageProps<"/pour-vous">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const [p, m] = await Promise.all([api<PageSuggestions>("/api/v1/pour-vous/", { query: { page: sp.page } }), moi()])
  const reglages = (
    <BoutonLien href="/profil?onglet=preferences" variant="outline" size="lg">
      <SlidersHorizontalIcon /> Modifier mes préférences
    </BoutonLien>
  )

  return (
    <Panneau>
      <EnTetePage titre={m.prenom ? `Vos suggestions, ${m.prenom}` : "Vos suggestions"} actions={reglages}>
        {p.profil_vide ? (
          "Vos suggestions apparaîtront ici une fois votre profil renseigné."
        ) : (
          <>
            <strong className="font-semibold text-foreground">
              {entier(p.total)} {pluriel(p.total, "offre ouverte", "offres ouvertes")}
            </strong>{" "}
            avec un score d&apos;au moins {p.seuil} %, la plus pertinente en premier.
          </>
        )}
      </EnTetePage>

      {!p.profil_vide && p.resume.length > 0 && (
        <div className="mt-8 flex flex-wrap items-center gap-6 rounded-[22px] verre-carte p-5">
          <Anneau valeur={p.completion} libelle={`Profil complété à ${p.completion} %`} />
          <dl className="grid flex-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
            {p.resume.map((r) => (
              <div key={r.titre} className="min-w-0">
                <dt className="text-xs font-medium text-muted-foreground">{r.titre}</dt>
                <dd className="mt-1 flex flex-wrap gap-1">
                  {r.valeurs.map((v) => (
                    <span key={v} className="rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground">
                      {v}
                    </span>
                  ))}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {p.profil_vide ? (
        <Vide
          titre="Dites-nous ce que vous cherchez."
          action={
            <BoutonLien href="/profil" size="lg">
              Compléter mon profil
            </BoutonLien>
          }
        >
          Votre pays, vos domaines et vos compétences suffisent pour commencer. Profil complété à {p.completion} %.
        </Vide>
      ) : p.resultats.length === 0 ? (
        <Vide titre="Aucune offre ouverte n'atteint votre seuil." action={reglages}>
          Élargissez vos lieux ou vos domaines, ou baissez le seuil de pertinence ({p.seuil} %).
        </Vide>
      ) : (
        <div className="mt-8">
          <GrilleOffres offres={p.resultats} admin={m.admin} />
        </div>
      )}

      <Pagination page={p.page} pages={p.pages} total={p.total} parPage={p.par_page} href={(n) => `/pour-vous?page=${n}`} />
    </Panneau>
  )
}
