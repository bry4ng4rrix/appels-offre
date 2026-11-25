"use client"

import { CheckIcon } from "lucide-react"
import { useState } from "react"

import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox"
import { cn } from "@/lib/utils"

export type Option = { valeur: string; libelle: string }

const libelle = (o: Option) => o.libelle
const egal = (a: Option, b: Option) => a.valeur === b.valeur

/** Plusieurs choix dans une longue liste (secteurs, pays) : puces + recherche.
 *  Les valeurs partent dans le formulaire par des champs caches, un par choix. */
export function ChoixMultiples({ id, nom, options, valeurs, placeholder }: { id: string; nom: string; options: Option[]; valeurs: string[]; placeholder: string }) {
  const [choisis, setChoisis] = useState<Option[]>(() => options.filter((o) => valeurs.includes(o.valeur)))
  const ancre = useComboboxAnchor()
  return (
    <>
      <Combobox multiple items={options} value={choisis} onValueChange={(v: Option[]) => setChoisis(v)} itemToStringLabel={libelle} isItemEqualToValue={egal}>
        <ComboboxChips ref={ancre} className="min-h-10 bg-card">
          <ComboboxValue>
            {(liste: Option[]) => (
              <>
                {liste.map((o) => (
                  <ComboboxChip key={o.valeur}>{o.libelle}</ComboboxChip>
                ))}
                <ComboboxChipsInput id={id} placeholder={liste.length ? "" : placeholder} />
              </>
            )}
          </ComboboxValue>
        </ComboboxChips>
        <ComboboxContent anchor={ancre}>
          <ComboboxEmpty>Aucun résultat.</ComboboxEmpty>
          <ComboboxList>
            {(o: Option) => (
              <ComboboxItem key={o.valeur} value={o}>
                {o.libelle}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
      {choisis.map((o) => (
        <input key={o.valeur} type="hidden" name={nom} value={o.valeur} />
      ))}
    </>
  )
}

/** Un seul choix dans une longue liste, avec recherche. */
export function ChoixUnique({ id, nom, options, valeur, placeholder }: { id: string; nom: string; options: Option[]; valeur?: string | null; placeholder: string }) {
  const [choisi, setChoisi] = useState<Option | null>(() => options.find((o) => o.valeur === valeur) ?? null)
  return (
    <>
      <Combobox items={options} value={choisi} onValueChange={(v: Option | null) => setChoisi(v)} itemToStringLabel={libelle} isItemEqualToValue={egal}>
        <ComboboxInput id={id} placeholder={placeholder} showClear={!!choisi} className="w-full bg-card" />
        <ComboboxContent>
          <ComboboxEmpty>Aucun résultat.</ComboboxEmpty>
          <ComboboxList>
            {(o: Option) => (
              <ComboboxItem key={o.valeur} value={o}>
                {o.libelle}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
      <input type="hidden" name={nom} value={choisi?.valeur ?? ""} />
    </>
  )
}

/** Quelques choix courts (regions, types d'offres) : des puces a cocher. */
export function Puces({ nom, options, valeurs, etiquette }: { nom: string; options: Option[]; valeurs: string[]; etiquette: string }) {
  const [choisis, setChoisis] = useState<string[]>(valeurs)
  return (
    <div role="group" aria-label={etiquette} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const actif = choisis.includes(o.valeur)
        return (
          <label
            key={o.valeur}
            className={cn(
              "inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors select-none has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
              actif ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:border-primary/40",
            )}
          >
            <input
              type="checkbox"
              name={nom}
              value={o.valeur}
              checked={actif}
              onChange={() => setChoisis((c) => (actif ? c.filter((v) => v !== o.valeur) : [...c, o.valeur]))}
              className="sr-only"
            />
            {actif && <CheckIcon className="size-3.5" aria-hidden />}
            {o.libelle}
          </label>
        )
      })}
    </div>
  )
}
