"use client"

import { AnimatePresence, motion } from "motion/react"
import { ExternalLinkIcon, LockKeyholeOpenIcon, SparklesIcon } from "lucide-react"
import Link from "next/link"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { useDico } from "@/components/app/traductions"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { consulter } from "@/lib/actions/offres"
import type { Credits } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, pl } from "@/lib/i18n"

type Props = { id: string; dejaConsultee: boolean; credits: Credits; lienAdmin?: string | null; aUnLien: boolean }

/** Ouvre l'annonce officielle. Le credit est debite par le serveur ; le compteur de
 *  l'en-tete roule de lui-meme au rafraichissement. */
export function Consulter({ id, dejaConsultee, credits, lienAdmin, aUnLien }: Props) {
  const d = useDico()
  const [lien, setLien] = useState<string | null>(lienAdmin ?? null)
  const [epuise, setEpuise] = useState(false)
  const [enCours, demarrer] = useTransition()
  const total = credits.total ?? 0
  const gratuit = dejaConsultee || credits.illimites

  if (!aUnLien)
    return <p className="text-sm text-muted-foreground">{d.consulter.sansLien}</p>

  function ouvrir() {
    // Onglet ouvert pendant le clic : apres l'appel, le navigateur le bloquerait.
    const onglet = window.open("", "_blank")
    demarrer(async () => {
      const r = await consulter(id)
      if (r.ok) {
        setLien(r.lien)
        if (onglet) {
          onglet.opener = null
          onglet.location.href = r.lien
        }
        if (!gratuit) {
          const reste = r.credits.total ?? 0
          toast.success(f(pl(d, reste, d.consulter.ouverte_un, d.consulter.ouverte), { n: reste }))
        }
      } else {
        onglet?.close()
        if (r.epuises) setEpuise(true)
        else toast.error(r.erreur)
      }
    })
  }

  return (
    <div className="grid gap-3">
      <AnimatePresence mode="wait" initial={false}>
        {lien ? (
          <motion.div
            key="lien"
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
            className="grid gap-2"
          >
            <Button nativeButton={false} size="lg" className="h-auto min-h-12 w-full py-2.5 text-base whitespace-normal" render={<a href={lien} target="_blank" rel="noopener noreferrer" />}>
              <ExternalLinkIcon /> {d.consulter.ouvrir}
            </Button>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <LockKeyholeOpenIcon className="size-3.5" /> {d.consulter.debloquee}
            </p>
          </motion.div>
        ) : (
          <motion.div key="bouton" exit={{ opacity: 0, y: -6 }} className="grid gap-2">
            <Button size="lg" className="h-auto min-h-12 w-full py-2.5 text-base whitespace-normal" onClick={ouvrir} disabled={enCours || (!gratuit && total === 0)}>
              {enCours ? <Spinner /> : <SparklesIcon />} {d.consulter.consulter}
            </Button>
            <p className="text-xs text-muted-foreground">
              {credits.essai_jusqu_au
                ? f(d.consulter.essai, { date: formateurs(d.locale).date(credits.essai_jusqu_au) })
                : gratuit
                ? d.consulter.dejaOuverte
                : total > 0
                  ? f(d.consulter.utilise, { n: total })
                  : d.consulter.plusDeCredits}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {(epuise || (!gratuit && total === 0 && !lien)) && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            <Alert className="border-urgent/30 bg-urgent/5">
              <AlertTitle>{d.consulter.epuisesTitre}</AlertTitle>
              <AlertDescription>
                {d.consulter.epuisesTexte}{" "}
                <Link href="/abonnement" className="font-medium text-primary underline underline-offset-4">
                  {d.consulter.choisirPlan}
                </Link>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
