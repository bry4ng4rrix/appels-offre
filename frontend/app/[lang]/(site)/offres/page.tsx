import { DownloadIcon, MapIcon } from "lucide-react"
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
import { formateurs } from "@/lib/format"
import { f, libelle, pl } from "@/lib/i18n"
import { moi, reference } from "@/lib/session"
import { cn } from "@/lib/utils"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("offres")

// Export des offres filtrees (admins) : le fichier passe par /bff avec la session.
const EXPORT = "inline-flex h-11 items-center gap-2 rounded-full bg-secondary px-5 text-sm font-medium transition-colors hover:bg-muted"

const FILTRES = ["etat", "q", "secteur", "pays", "nature", "region", "lieu", "date_de", "date_a"] as const


const PASTILLE: Record<EtatEcheance, string> = {
  urgente: "bg-urgent",
  proche: "bg-proche",
  lointaine: "bg-lointaine",
  passee: "bg-muted-foreground/50",
  presumee: "bg-muted-foreground/50",
  inconnue: "bg-muted-foreground/30",
}

export default function PageOffresListe({ searchParams }: PageProps<"/[lang]/offres">) {
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

async function Offres({ searchParams }: Pick<PageProps<"/[lang]/offres">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const valeurs = Object.fromEntries(FILTRES.map((k) => [k, sp[k]]))
  const etat = valeurs.etat ?? "toutes"
  const [ref, page, m, d] = await Promise.all([
    reference(),
    api<PageOffres>("/api/v1/offres/", { query: { ...valeurs, page: sp.page } }),
    moi(),
    dico(),
  ])
  const { entier } = formateurs(d.locale)
  const sansEtat = { ...valeurs, etat: undefined }
  const carte = avecParams("/carte", { ...valeurs }, {})

  return (
    <>
      <Onglets
        actif={etat}
        onglets={ref.etats.map((e) => ({
          code: e.code,
          libelle: libelle(d.etats, e.code, e.libelle),
          href: avecParams("/offres", sansEtat, { etat: e.code === "toutes" ? undefined : e.code }),
          nombre: e.code === etat ? page.total : undefined,
        }))}
      />
      <Panneau className={etat === ref.etats[0]?.code ? "" : ""}>
      <EnTetePage
        titre={f(pl(d, page.total, d.offres.total_un, d.offres.total), { n: entier(page.total) })}
        actions={
          <>
            {m.admin && (
              <>
                <a href={avecParams("/bff/admin/exporter", valeurs, { format: "csv" })} download className={EXPORT}>
                  <DownloadIcon className="size-4" /> CSV
                </a>
                <a href={avecParams("/bff/admin/exporter", valeurs, { format: "json" })} download className={EXPORT}>
                  <DownloadIcon className="size-4" /> JSON
                </a>
              </>
            )}
            <BoutonLien href={carte} variant="outline" size="lg">
              <MapIcon /> {d.offres.voirCarte}
            </BoutonLien>
          </>
        }
      >
        {libelle(d.offres.explications, etat, d.offres.explications.toutes)}
      </EnTetePage>

      <div className="mt-6">
        <FiltresOffres valeurs={valeurs} secteurs={ref.secteurs} pays={ref.pays} regions={ref.regions.map((r) => ({ ...r, libelle: libelle(d.regions, r.code, r.libelle) }))} />
      </div>

      {page.resultats.length === 0 ? (
        <Vide
          titre={d.offres.videTitre}
          action={
            <BoutonLien href="/offres" variant="outline">
              {d.filtres.reinitialiser}
            </BoutonLien>
          }
        >
          {etat === "actionnables"
            ? d.offres.videActionnables
            : d.offres.videTexte}
        </Vide>
      ) : (
        <div className="mt-10 grid gap-12">
          {grouper(page.resultats).map((g, i) => (
            <section key={`${g.etat}-${i}`} aria-labelledby={`groupe-${i}`}>
              <h3 id={`groupe-${i}`} className="mb-4 flex items-center gap-2.5 text-[0.95rem] font-medium">
                <span className={cn("size-2.5 rounded-full", PASTILLE[g.etat])} aria-hidden />
                {d.groupes[g.etat]}
                <span className="rounded-full verre-carte px-2 text-xs text-muted-foreground tabular-nums ">{g.offres.length}</span>
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
