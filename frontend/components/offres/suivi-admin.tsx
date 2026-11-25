"use client"

import { CheckIcon, XIcon } from "lucide-react"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { decider, juger } from "@/lib/actions/offres"
import type { Choix, StatutSuivi } from "@/lib/api/types"
import { libelle } from "@/lib/i18n"
import { cn } from "@/lib/utils"

const COULEURS: Record<string, string> = {
  gagne: "data-[pressed]:bg-lointaine data-[pressed]:text-sur-vif",
  perdu: "data-[pressed]:bg-urgent data-[pressed]:text-sur-vif",
  candidature: "data-[pressed]:bg-primary data-[pressed]:text-primary-foreground",
  hors_sujet: "data-[pressed]:bg-muted-foreground data-[pressed]:text-background",
  a_etudier: "data-[pressed]:bg-foreground data-[pressed]:text-background",
}

/** Statut commercial et note : reserve aux admins. */
export function SuiviAdmin({ id, statuts, statut, note }: { id: string; statuts: Choix[]; statut?: StatutSuivi; note?: string }) {
  const d = useDico()
  const [courant, setCourant] = useState<string | undefined>(statut)
  const [texte, setTexte] = useState(note ?? "")
  const [enCours, demarrer] = useTransition()

  function enregistrer(s: StatutSuivi, n = texte) {
    demarrer(async () => {
      const r = await decider(id, s, n)
      if (r.ok) toast.success(r.message)
      else {
        toast.error(r.erreur)
        setCourant(statut)
      }
    })
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-2">
        <span className="text-sm font-medium">{d.admin.statutCommercial}</span>
        <ToggleGroup
          value={courant ? [courant] : []}
          onValueChange={(v: string[]) => {
            const s = v[0] as StatutSuivi | undefined
            if (!s) return
            setCourant(s)
            enregistrer(s)
          }}
          variant="outline"
          size="sm"
          className="flex-wrap"
          spacing={1}
        >
          {statuts.map((s) => (
            <ToggleGroupItem key={s.code} value={s.code} className={cn("text-xs", COULEURS[s.code])}>
              {s.code === "candidature" ? d.admin.candidater : libelle(d.statuts, s.code, s.libelle)}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="note">{d.admin.noteInterne}</Label>
        <Textarea id="note" value={texte} onChange={(e) => setTexte(e.target.value)} rows={3} placeholder={d.admin.notePlaceholder} />
        <Button variant="outline" size="sm" className="justify-self-start" disabled={!courant || enCours} onClick={() => courant && enregistrer(courant as StatutSuivi)}>
          {enCours && <Spinner />} {d.admin.enregistrerNote}
        </Button>
      </div>
    </div>
  )
}

export function Verdict({ id, pertinent }: { id: string; pertinent: boolean }) {
  const d = useDico()
  const [enCours, demarrer] = useTransition()
  const basculer = () =>
    demarrer(async () => {
      const r = await juger(id, !pertinent)
      if (r.ok) toast.success(r.message)
      else toast.error(r.erreur)
    })
  return (
    <Button variant={pertinent ? "outline" : "default"} size="sm" onClick={basculer} disabled={enCours}>
      {enCours ? <Spinner /> : pertinent ? <XIcon /> : <CheckIcon />}
      {pertinent ? d.admin.ecarter : d.admin.retenir}
    </Button>
  )
}
