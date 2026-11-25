"use client"

import { AnimatePresence, motion } from "motion/react"
import { SearchIcon, XIcon } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import { useState, useTransition } from "react"

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
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Choix } from "@/lib/api/types"

type Valeurs = Record<string, string | undefined>
type Props = {
  valeurs: Valeurs
  secteurs: Choix[]
  pays: Choix[]
  regions: Choix[]
  /** Champs a garder dans l'URL sans les afficher (etat, lieu). */
  caches?: string[]
}

const NATURES: Choix[] = [
  { code: "marche", libelle: "Marchés" },
  { code: "emploi", libelle: "Postes" },
  { code: "inconnue", libelle: "Non qualifiée" },
]
const TOUS = "__tous"

/** Un choix parmi une longue liste, avec recherche (secteurs, pays). */
function ChoixCherchable({
  id,
  libelle,
  items,
  valeur,
  tous,
  onChange,
}: {
  id: string
  libelle: string
  items: Choix[]
  valeur?: string
  tous: string
  onChange: (v: string | undefined) => void
}) {
  const courant = items.find((i) => i.code === valeur) ?? null
  return (
    <div className="grid gap-1.5">
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
          <ComboboxEmpty>Aucun résultat.</ComboboxEmpty>
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
}: {
  libelle: string
  items: Choix[]
  valeur?: string
  tous: string
  onChange: (v: string | undefined) => void
}) {
  const tout = [{ code: TOUS, libelle: tous }, ...items]
  return (
    <div className="grid gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{libelle}</span>
      <Select
        items={tout.map((i) => ({ value: i.code, label: i.libelle }))}
        value={valeur ?? TOUS}
        onValueChange={(v) => onChange(v === TOUS || v === null ? undefined : String(v))}
      >
        <SelectTrigger className="w-full" aria-label={libelle}>
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
  const router = useRouter()
  const pathname = usePathname()
  const [enCours, demarrer] = useTransition()
  const [q, setQ] = useState(valeurs.q ?? "")

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
        <InputGroup className="h-12 rounded-full bg-card pl-1.5 text-base shadow-xs">
          <InputGroupAddon>
            <SearchIcon className="size-5" />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            name="q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Titre, organisation ou catégorie, puis Entrée"
            aria-label="Rechercher une offre"
            className="text-base"
          />
          {caches.map((c) => valeurs[c] && <input key={c} type="hidden" name={c} value={valeurs[c]} />)}
        </InputGroup>
      </form>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-[1.3fr_1.3fr_1fr_1fr_auto_auto]">
        <ChoixCherchable id="f-secteur" libelle="Secteur" items={secteurs} valeur={valeurs.secteur} tous="Tous les secteurs" onChange={(v) => appliquer({ secteur: v })} />
        <ChoixCherchable id="f-pays" libelle="Pays" items={pays} valeur={valeurs.pays} tous="Tous les pays" onChange={(v) => appliquer({ pays: v })} />
        <ChoixSimple libelle="Nature" items={NATURES} valeur={valeurs.nature} tous="Marchés et postes" onChange={(v) => appliquer({ nature: v })} />
        <ChoixSimple libelle="Région" items={regions} valeur={valeurs.region} tous="Toutes" onChange={(v) => appliquer({ region: v })} />
        <div className="grid gap-1.5">
          <Label htmlFor="f-de" className="text-xs text-muted-foreground">
            Échéance du
          </Label>
          <Input id="f-de" type="date" defaultValue={valeurs.date_de} onChange={(e) => appliquer({ date_de: e.target.value || undefined })} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-a" className="text-xs text-muted-foreground">
            au
          </Label>
          <Input id="f-a" type="date" defaultValue={valeurs.date_a} onChange={(e) => appliquer({ date_a: e.target.value || undefined })} />
        </div>
      </div>
      {actifs && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {valeurs.lieu && (
            <Button variant="secondary" size="sm" onClick={() => appliquer({ lieu: undefined })}>
              Lieu : {valeurs.lieu} <XIcon />
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
            <XIcon /> Réinitialiser les filtres
          </Button>
        </div>
      )}
    </section>
  )
}
