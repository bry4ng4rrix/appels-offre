"use client"

import { useTransition } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { demanderPlan } from "@/lib/actions/compte"

export function DemanderPlan({ plan, vedette }: { plan: number; vedette?: boolean }) {
  const [enCours, demarrer] = useTransition()
  return (
    <Button
      size="lg"
      variant={vedette ? "default" : "outline"}
      className="h-11 w-full"
      disabled={enCours}
      onClick={() =>
        demarrer(async () => {
          const r = await demanderPlan(plan)
          if (r.ok) toast.success(r.message ?? "Demande envoyée.")
          else toast.error(r.erreur)
        })
      }
    >
      {enCours && <Spinner />} Demander ce plan
    </Button>
  )
}
