import { MapIcon } from "lucide-react"
import type { Metadata } from "next"
import { Suspense } from "react"

import { BoutonLien } from "@/components/app/bouton-lien"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, GrilleSquelette, Pagination, Vide, aplatir, avecParams } from "@/components/app/page"
import { GrilleOffres } from "@/components/offres/carte-offre"
import { FiltresOffres } from "@/components/offres/filtres"
import { Onglets } from "@/components/offres/onglets"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { EtatEcheance, Offre, PageOffres } from "@/lib/api/types"
import { GROUPES, entier, pluriel } from "@/lib/format"
import { moi, reference } from "@/lib/session"
import { cn } from "@/lib/utils"

export const metadata: Metadata = { title: "Offres" }

const FILTRES = ["etat", "q", "secteur", "pays", "nature", "region", "lieu", "date_de", "date_a"] as const

const EXPLICATIONS: Record<string, string> = {
  actionnables: "Retenues et encore ouvertes : ce sur quoi on peut agir.",
  retenues: "Toutes les retenues, échéances passées comprises.",
  cloturees: "Date limite passée, ou retirées ou annoncées closes par la source.",
  retirees: "Constatées disparues ou closes chez la source.",
  "sans-echeance": "Retenues sans date limite, publiées il y a plus de 30 jours : présumées closes, à vérifier.",
  ecartees: "Écartées par le tri, conservées pour contrôler les règles.",
  toutes: "Toute la base, hors offres clôturées ou expirées.",
}

const PASTILLE: Record<EtatEcheance, string> = {
  urgente: "bg-urgent",
  proche: "bg-proche",
  lointaine: "bg-lointaine",
  passee: "bg-muted-foreground/50",
  presumee: "bg-muted-foreground/50",
  inconnue: "bg-muted-foreground/30",
}

export default function PageOffresListe({ searchParams }: PageProps<"/offres">) {
  return (
    <Suspense fallback={<Chargement />}>
      <Offres searchParams={searchParams} />
    </Suspense>
  )
}

function Chargement() {
  return (
    <>
      <Skeleton className="h-12 w-full max-w-2xl rounded-full" />
      <div className="mt-2 rounded-[30px] bg-panneau p-8">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-6 h-12 w-full rounded-full" />
        <div className="mt-10">
          <GrilleSquelette n={9} />
        </div>
      </div>
    </>
  )
}

/** Les offres de la page, par groupe d'echeance, dans l'ordre ou l'API les rend. */
function grouper(offres: Offre[]) {
  const groupes: { etat: EtatEcheance; offres: Offre[] }[] = []
  for (const o of offres) {
    const dernier = groupes.at(-1)
    if (dernier?.etat === o.etat_echeance) dernier.offres.push(o)
    else groupes.push({ etat: o.etat_echeance, offres: [o] })
  }
  return groupes
}

async function Offres({ searchParams }: Pick<PageProps<"/offres">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const valeurs = Object.fromEntries(FILTRES.map((k) => [k, sp[k]]))
  const etat = valeurs.etat ?? "toutes"
  const [ref, page, m] = await Promise.all([
    reference(),
    api<PageOffres>("/api/v1/offres/", { query: { ...valeurs, page: sp.page } }),
    moi(),
  ])
  const sansEtat = { ...valeurs, etat: undefined }
  const carte = avecParams("/carte", { ...valeurs }, {})

  return (
    <>
      <Onglets
        actif={etat}
        onglets={ref.etats.map((e) => ({
          code: e.code,
          libelle: e.libelle,
          href: avecParams("/offres", sansEtat, { etat: e.code === "toutes" ? undefined : e.code }),
          nombre: e.code === etat ? page.total : undefined,
        }))}
      />
      <Panneau className={etat === ref.etats[0]?.code ? "rounded-tl-none" : ""}>
      <EnTetePage
        titre={`${entier(page.total)} ${pluriel(page.total, "offre")}`}
        actions={
          <BoutonLien href={carte} variant="outline" size="lg">
            <MapIcon /> Voir sur la carte
          </BoutonLien>
        }
      >
        {EXPLICATIONS[etat] ?? EXPLICATIONS.toutes}
      </EnTetePage>

      <div className="mt-6">
        <FiltresOffres valeurs={valeurs} secteurs={ref.secteurs} pays={ref.pays} regions={ref.regions} />
      </div>

      {page.resultats.length === 0 ? (
        <Vide
          titre="Aucune offre ne correspond à ces filtres."
          action={
            <BoutonLien href="/offres" variant="outline">
              Réinitialiser les filtres
            </BoutonLien>
          }
        >
          {etat === "actionnables"
            ? "Une offre dont l'échéance est passée n'apparaît pas ici : essayez l'onglet « Retenues »."
            : "Élargissez la recherche ou retirez un filtre."}
        </Vide>
      ) : (
        <div className="mt-10 grid gap-12">
          {grouper(page.resultats).map((g, i) => (
            <section key={`${g.etat}-${i}`} aria-labelledby={`groupe-${i}`}>
              <h3 id={`groupe-${i}`} className="mb-4 flex items-center gap-2.5 text-[0.95rem] font-medium">
                <span className={cn("size-2.5 rounded-full", PASTILLE[g.etat])} aria-hidden />
                {GROUPES[g.etat]}
                <span className="rounded-full bg-card px-2 text-xs text-muted-foreground tabular-nums ring-1 ring-border/70">{g.offres.length}</span>
              </h3>
              <GrilleOffres offres={g.offres} admin={m.admin} />
            </section>
          ))}
        </div>
      )}

      <Pagination
        page={page.page}
        pages={page.pages}
        total={page.total}
        parPage={page.par_page}
        href={(n) => avecParams("/offres", valeurs, { page: n })}
      />
      </Panneau>
    </>
  )
}
