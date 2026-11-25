"use client"

import { CalendarClockIcon, CopyIcon, Share2Icon } from "lucide-react"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { useDico } from "@/components/app/traductions"
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

export function CopierLien({ lien, libelle }: { lien: string; libelle?: string }) {
  const d = useDico()
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() =>
        navigator.clipboard.writeText(lien).then(
          () => toast.success(d.commun.lienCopie),
          () => toast.error(d.commun.copieRefusee),
        )
      }
    >
      <CopyIcon /> {libelle ?? d.commun.copierLien}
    </Button>
  )
}

/** Copie l'adresse de la fiche (pas le lien officiel) pour l'envoyer a un collegue. */
export function PartagerOffre({ href }: { href: string }) {
  const d = useDico()
  return (
    <Button
      variant="secondary"
      size="lg"
      className="h-10"
      onClick={() =>
        navigator.clipboard.writeText(new URL(href, window.location.origin).toString()).then(
          () => toast.success(d.commun.lienFicheCopie),
          () => toast.error(d.commun.copieRefusee),
        )
      }
    >
      <Share2Icon /> {d.commun.partager}
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
  const d = useDico()
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
              <CalendarClockIcon /> {d.carte.echeance}
            </Button>
          ) : (
            <Button variant="outline" size="sm">
              <CalendarClockIcon /> {d.carte.echeance}
            </Button>
          ))
        }
      />
      <DialogContent className="sm:max-w-sm">
        <form onSubmit={enregistrer} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>{d.admin.modifierEcheance}</DialogTitle>
            <DialogDescription>{d.admin.modifierEcheanceAide}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor={`echeance-${id}`}>{d.admin.dateRemise}</Label>
            <Input id={`echeance-${id}`} type="date" required value={valeur} onChange={(e) => setValeur(e.target.value)} />
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" type="button" />}>{d.commun.annuler}</DialogClose>
            <Button type="submit" disabled={enCours}>
              {enCours && <Spinner />} {d.commun.enregistrer}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
