"use client"

import { CheckIcon, PencilIcon, PlusIcon, XIcon } from "lucide-react"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { Champ } from "@/components/app/champ"
import { useFormulaire } from "@/components/app/formulaire"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { deciderAbonnement, enregistrerPlan } from "@/lib/actions/admin"
import type { Plan } from "@/lib/api/types"

export function DeciderDemande({ id }: { id: number }) {
  const [enCours, demarrer] = useTransition()
  const [action, setAction] = useState<"valider" | "refuser" | null>(null)
  const agir = (a: "valider" | "refuser") => {
    setAction(a)
    demarrer(async () => {
      const r = await deciderAbonnement(id, a)
      if (r.ok) toast.success(r.message ?? (a === "valider" ? "Abonnement validé." : "Demande refusée."))
      else toast.error(r.erreur)
    })
  }
  return (
    <div className="flex gap-2">
      <Button variant="secondary" disabled={enCours} onClick={() => agir("refuser")}>
        {enCours && action === "refuser" ? <Spinner /> : <XIcon />} Refuser
      </Button>
      <Button disabled={enCours} onClick={() => agir("valider")}>
        {enCours && action === "valider" ? <Spinner /> : <CheckIcon />} Valider
      </Button>
    </div>
  )
}

/** Creer ou modifier un plan. Les regles (credits >= 1...) sont celles du serveur. */
export function DialoguePlan({ plan }: { plan?: Plan }) {
  const [ouvert, setOuvert] = useState(false)
  const [parJour, setParJour] = useState(plan?.par_jour ?? false)
  const [actif, setActif] = useState(plan?.actif ?? true)
  const action = async (p: Parameters<typeof enregistrerPlan>[1], f: FormData) => {
    const r = await enregistrerPlan(plan?.id ?? null, p, f)
    if (r.ok) setOuvert(false)
    return r
  }
  const { surEnvoi, enCours, erreurs } = useFormulaire(action)
  return (
    <Dialog open={ouvert} onOpenChange={setOuvert}>
      <DialogTrigger
        render={
          plan ? (
            <Button variant="secondary" size="sm">
              <PencilIcon /> Modifier
            </Button>
          ) : (
            <Button size="lg">
              <PlusIcon /> Nouveau plan
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-md">
        <form onSubmit={surEnvoi} className="grid gap-5">
          <DialogHeader>
            <DialogTitle>{plan ? `Modifier « ${plan.nom} »` : "Nouveau plan"}</DialogTitle>
            <DialogDescription>Un plan par jour ajoute des crédits chaque jour ; sinon, c&apos;est un lot à utiliser quand on veut.</DialogDescription>
          </DialogHeader>
          <Champ nom="nom" libelle="Nom" erreurs={erreurs}>
            <Input id="nom" name="nom" defaultValue={plan?.nom} required />
          </Champ>
          <div className="grid grid-cols-2 gap-4">
            <Champ nom="prix" libelle="Prix (Ar)" erreurs={erreurs}>
              <Input id="prix" name="prix" type="number" min={0} defaultValue={plan?.prix} required />
            </Champ>
            <Champ nom="credits" libelle="Crédits" erreurs={erreurs}>
              <Input id="credits" name="credits" type="number" min={1} defaultValue={plan?.credits} required />
            </Champ>
          </div>
          <div className="flex items-center justify-between rounded-2xl bg-muted p-3.5">
            <Label htmlFor="par_jour">Crédits chaque jour</Label>
            <Switch id="par_jour" checked={parJour} onCheckedChange={setParJour} />
            <input type="hidden" name="par_jour" value={parJour ? "on" : ""} />
          </div>
          <Champ nom="duree_jours" libelle="Durée (jours)" aide="Vide : sans date limite." erreurs={erreurs}>
            <Input id="duree_jours" name="duree_jours" type="number" min={1} defaultValue={plan?.duree_jours ?? ""} />
          </Champ>
          <div className="flex items-center justify-between rounded-2xl bg-muted p-3.5">
            <Label htmlFor="actif">Proposé aux utilisateurs</Label>
            <Switch id="actif" checked={actif} onCheckedChange={setActif} />
            <input type="hidden" name="actif" value={actif ? "on" : ""} />
          </div>
          <DialogFooter>
            <Button type="submit" size="lg" disabled={enCours}>
              {enCours && <Spinner />} Enregistrer
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
