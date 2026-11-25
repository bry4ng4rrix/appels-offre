import { SlidersHorizontalIcon } from "lucide-react"
import { Suspense } from "react"

import { Anneau } from "@/components/app/anneau"
import { BoutonLien } from "@/components/app/bouton-lien"
import { Panneau } from "@/components/app/coque"
import { EnTetePage, GrilleSquelette, Pagination, Vide, aplatir } from "@/components/app/page"
import { GrilleOffres } from "@/components/offres/carte-offre"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api/serveur"
import type { PageSuggestions } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, pl } from "@/lib/i18n"
import { moi } from "@/lib/session"
import { dico, titre } from "@/lib/i18n/serveur"

export const generateMetadata = titre("pourVous")

export default function PagePourVous({ searchParams }: PageProps<"/[lang]/pour-vous">) {
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

async function Suggestions({ searchParams }: Pick<PageProps<"/[lang]/pour-vous">, "searchParams">) {
  const sp = aplatir(await searchParams)
  const [p, m, d] = await Promise.all([api<PageSuggestions>("/api/v1/pour-vous/", { query: { page: sp.page } }), moi(), dico()])
  const { entier } = formateurs(d.locale)
  const reglages = (
    <BoutonLien href="/profil?onglet=preferences" variant="outline" size="lg">
      <SlidersHorizontalIcon /> {d.pourVous.modifierPreferences}
    </BoutonLien>
  )

  return (
    <Panneau>
      <EnTetePage titre={m.prenom ? f(d.pourVous.titrePrenom, { prenom: m.prenom }) : d.pourVous.titre} actions={reglages}>
        {p.profil_vide ? (
          d.pourVous.profilVide
        ) : (
          <>
            <strong className="font-semibold text-foreground">
              {f(pl(d, p.total, d.pourVous.total_un, d.pourVous.total), { n: entier(p.total) })}
            </strong>{" "}
            {f(d.pourVous.seuil, { seuil: p.seuil })}
          </>
        )}
      </EnTetePage>

      {!p.profil_vide && p.resume.length > 0 && (
        <div className="mt-8 flex flex-wrap items-center gap-6 rounded-[22px] verre-carte p-5">
          <Anneau valeur={p.completion} libelle={f(d.pourVous.completion, { n: p.completion })} />
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
          titre={d.pourVous.videTitre}
          action={
            <BoutonLien href="/profil" size="lg">
              {d.pourVous.completer}
            </BoutonLien>
          }
        >
          {f(d.pourVous.videTexte, { n: p.completion })}
        </Vide>
      ) : p.resultats.length === 0 ? (
        <Vide titre={d.pourVous.seuilTitre} action={reglages}>
          {f(d.pourVous.seuilTexte, { seuil: p.seuil })}
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
