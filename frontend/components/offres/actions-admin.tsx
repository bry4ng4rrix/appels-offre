"use client"

import { CalendarClockIcon, CopyIcon, Share2Icon } from "lucide-react"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { dater } from "@/lib/actions/offres"

export function CopierLien({ lien, libelle = "Copier le lien" }: { lien: string; libelle?: string }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() =>
        navigator.clipboard.writeText(lien).then(
          () => toast.success("Lien copié dans le presse-papier."),
          () => toast.error("Copie refusée par le navigateur."),
        )
      }
    >
      <CopyIcon /> {libelle}
    </Button>
  )
}

/** Copie l'adresse de la fiche (pas le lien officiel) pour l'envoyer a un collegue. */
export function PartagerOffre({ href }: { href: string }) {
  return (
    <Button
      variant="secondary"
      size="lg"
      className="h-10"
      onClick={() =>
        navigator.clipboard.writeText(new URL(href, window.location.origin).toString()).then(
          () => toast.success("Lien de la fiche copié."),
          () => toast.error("Copie refusée par le navigateur."),
        )
      }
    >
      <Share2Icon /> Partager
    </Button>
  )
}

export function ModifierEcheance({
  id,
  dateLimite,
  declencheur,
  pilule = false,
}: {
  id: string
  dateLimite?: string | null
  declencheur?: React.ReactElement
  pilule?: boolean
}) {
  const [ouvert, setOuvert] = useState(false)
  const [valeur, setValeur] = useState(dateLimite ?? "")
  const [enCours, demarrer] = useTransition()

  function enregistrer(e: React.FormEvent) {
    e.preventDefault()
    demarrer(async () => {
      const r = await dater(id, valeur)
      if (r.ok) {
        toast.success(r.message)
        setOuvert(false)
      } else toast.error(r.erreur)
    })
  }

  return (
    <Dialog open={ouvert} onOpenChange={setOuvert}>
      <DialogTrigger
        render={
          declencheur ??
          (pilule ? (
            <Button variant="secondary" size="lg" className="h-10">
              <CalendarClockIcon /> Échéance
            </Button>
          ) : (
            <Button variant="outline" size="sm">
              <CalendarClockIcon /> Échéance
            </Button>
          ))
        }
      />
      <DialogContent className="sm:max-w-sm">
        <form onSubmit={enregistrer} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Modifier l&apos;échéance</DialogTitle>
            <DialogDescription>La date saisie remplace celle de la source, et l&apos;offre change de groupe.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor={`echeance-${id}`}>Date limite de remise</Label>
            <Input id={`echeance-${id}`} type="date" required value={valeur} onChange={(e) => setValeur(e.target.value)} />
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" type="button" />}>Annuler</DialogClose>
            <Button type="submit" disabled={enCours}>
              {enCours && <Spinner />} Enregistrer
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
