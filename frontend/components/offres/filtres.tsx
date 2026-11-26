"use client"

import { AnimatePresence, motion } from "motion/react"
import { SearchIcon, SlidersHorizontalIcon, XIcon } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import { useState, useTransition } from "react"

import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox"
import { Input } from "@/components/ui/input"
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Choix } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type Valeurs = Record<string, string | undefined>
type Props = {
  valeurs: Valeurs
  secteurs: Choix[]
  pays: Choix[]
  regions: Choix[]
  /** Champs a garder dans l'URL sans les afficher (etat, lieu). */
  caches?: string[]
}

const TOUS = "__tous"

/** Un choix parmi une longue liste, avec recherche (secteurs, pays). */
function ChoixCherchable({
  id,
  libelle,
  items,
  valeur,
  tous,
  onChange,
  className,
}: {
  id: string
  libelle: string
  items: Choix[]
  valeur?: string
  tous: string
  onChange: (v: string | undefined) => void
  className?: string
}) {
  const d = useDico()
  const courant = items.find((i) => i.code === valeur) ?? null
  return (
    <div className={cn("grid min-w-0 gap-1.5", className)}>
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {libelle}
      </Label>
      <Combobox
        items={items}
        value={courant}
        onValueChange={(v: Choix | null) => onChange(v?.code)}
        itemToStringLabel={(i: Choix) => i.libelle}
        isItemEqualToValue={(a: Choix, b: Choix) => a.code === b.code}
      >
        <ComboboxInput id={id} placeholder={tous} showClear={!!courant} className="w-full" />
        <ComboboxContent>
          <ComboboxEmpty>{d.commun.aucunResultat}</ComboboxEmpty>
          <ComboboxList>
            {(i: Choix) => (
              <ComboboxItem key={i.code} value={i}>
                {i.libelle}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </div>
  )
}

function ChoixSimple({
  libelle,
  items,
  valeur,
  tous,
  onChange,
  className,
}: {
  libelle: string
  items: Choix[]
  valeur?: string
  tous: string
  onChange: (v: string | undefined) => void
  className?: string
}) {
  const tout = [{ code: TOUS, libelle: tous }, ...items]
  return (
    <div className={cn("grid min-w-0 gap-1.5", className)}>
      <span className="text-xs font-medium text-muted-foreground">{libelle}</span>
      <Select
        items={tout.map((i) => ({ value: i.code, label: i.libelle }))}
        value={valeur ?? TOUS}
        onValueChange={(v) => onChange(v === TOUS || v === null ? undefined : String(v))}
      >
        <SelectTrigger className="w-full min-w-0" aria-label={libelle}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {tout.map((i) => (
            <SelectItem key={i.code} value={i.code}>
              {i.libelle}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function FiltresOffres({ valeurs, secteurs, pays, regions, caches = ["etat", "lieu"] }: Props) {
  const d = useDico()
  const natures: Choix[] = [
    { code: "marche", libelle: d.filtres.marches },
    { code: "emploi", libelle: d.filtres.postes },
    { code: "inconnue", libelle: d.nature.nonQualifiee },
  ]
  const router = useRouter()
  const pathname = usePathname()
  const [enCours, demarrer] = useTransition()
  const [q, setQ] = useState(valeurs.q ?? "")
  // Sur telephone, les filtres detailles se replient derriere un bouton : les offres restent visibles.
  const [ouvert, setOuvert] = useState(false)
  const nbFiltres = ["secteur", "pays", "nature", "region", "date_de", "date_a"].filter((k) => valeurs[k]).length

  function appliquer(changes: Valeurs) {
    const suivants: Valeurs = { ...valeurs, ...changes, page: undefined }
    const p = new URLSearchParams()
    for (const [k, v] of Object.entries(suivants)) if (v) p.set(k, v)
    demarrer(() => router.push(`${pathname}${p.size ? `?${p}` : ""}`, { scroll: false }))
  }

  const actifs = ["q", "secteur", "pays", "nature", "region", "date_de", "date_a", "lieu"].some((k) => valeurs[k])

  return (
    <section aria-label="Recherche et filtres" className="relative">
      <AnimatePresence>
        {enCours && (
          <motion.div
            className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-marque"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 0.85, transition: { duration: 2, ease: [0.1, 0.8, 0.2, 1] } }}
            exit={{ scaleX: 1, opacity: 0, transition: { duration: 0.25 } }}
          />
        )}
      </AnimatePresence>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          appliquer({ q: q.trim() || undefined })
        }}
        role="search"
      >
        <InputGroup className="h-12 rounded-full bg-card ps-1.5 pe-1 text-base shadow-xs">
          <InputGroupAddon>
            <SearchIcon className="size-5" />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            name="q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={d.filtres.recherche}
            aria-label={d.filtres.rechercheAria}
            className="text-base text-ellipsis"
          />
          <InputGroupAddon align="inline-end" className="md:hidden">
            <InputGroupButton
              size="icon-sm"
              variant={ouvert ? "default" : "secondary"}
              className="relative size-10 rounded-full"
              aria-label={d.filtres.filtres}
              aria-expanded={ouvert}
              aria-controls="filtres-detail"
              onClick={() => setOuvert((o) => !o)}
            >
              <SlidersHorizontalIcon className="size-[18px]" />
              {nbFiltres > 0 && (
                <span className="absolute -top-1 -end-1 grid min-w-4.5 place-items-center rounded-full bg-ambre px-1 text-[10px] leading-4.5 font-semibold text-ambre-foreground tabular-nums">
                  {nbFiltres}
                </span>
              )}
            </InputGroupButton>
          </InputGroupAddon>
          {caches.map((c) => valeurs[c] && <input key={c} type="hidden" name={c} value={valeurs[c]} />)}
        </InputGroup>
      </form>
      <div
        id="filtres-detail"
        className={cn("mt-3 grid-cols-2 gap-3 md:grid md:grid-cols-3 2xl:grid-cols-[1.3fr_1.3fr_1fr_1fr_auto_auto]", ouvert ? "grid" : "hidden")}
      >
        <ChoixCherchable id="f-secteur" libelle={d.filtres.secteur} items={secteurs} valeur={valeurs.secteur} tous={d.filtres.tousSecteurs} onChange={(v) => appliquer({ secteur: v })} className="col-span-2 md:col-span-1" />
        <ChoixCherchable id="f-pays" libelle={d.filtres.pays} items={pays} valeur={valeurs.pays} tous={d.filtres.tousPays} onChange={(v) => appliquer({ pays: v })} className="col-span-2 md:col-span-1" />
        <ChoixSimple libelle={d.filtres.nature} items={natures} valeur={valeurs.nature} tous={d.filtres.toutesNatures} onChange={(v) => appliquer({ nature: v })} className="col-span-2 md:col-span-1" />
        <ChoixSimple libelle={d.filtres.region} items={regions} valeur={valeurs.region} tous={d.commun.toutes} onChange={(v) => appliquer({ region: v })} className="col-span-2 md:col-span-1" />
        <div className="grid min-w-0 gap-1.5">
          <Label htmlFor="f-de" className="text-xs text-muted-foreground">
            {d.filtres.echeanceDu}
          </Label>
          <Input id="f-de" type="date" defaultValue={valeurs.date_de} onChange={(e) => appliquer({ date_de: e.target.value || undefined })} />
        </div>
        <div className="grid min-w-0 gap-1.5">
          <Label htmlFor="f-a" className="text-xs text-muted-foreground">
            {d.filtres.au}
          </Label>
          <Input id="f-a" type="date" defaultValue={valeurs.date_a} onChange={(e) => appliquer({ date_a: e.target.value || undefined })} />
        </div>
      </div>
      {actifs && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {valeurs.lieu && (
            <Button variant="secondary" size="sm" onClick={() => appliquer({ lieu: undefined })}>
              {d.filtres.lieu} {valeurs.lieu} <XIcon />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setQ("")
              demarrer(() => router.push(valeurs.etat ? `${pathname}?etat=${valeurs.etat}` : pathname, { scroll: false }))
            }}
          >
            <XIcon /> {d.filtres.reinitialiser}
          </Button>
        </div>
      )}
    </section>
  )
}
