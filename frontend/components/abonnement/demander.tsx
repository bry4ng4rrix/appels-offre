"use client"

import { useTransition } from "react"
import { toast } from "sonner"

import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { demanderPlan } from "@/lib/actions/compte"

export function DemanderPlan({ plan, vedette }: { plan: number; vedette?: boolean }) {
  const d = useDico()
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
          if (r.ok) toast.success(r.message ?? d.plan.demandeEnvoyee)
          else toast.error(r.erreur)
        })
      }
    >
      {enCours && <Spinner />} {d.plan.demander}
    </Button>
  )
}
