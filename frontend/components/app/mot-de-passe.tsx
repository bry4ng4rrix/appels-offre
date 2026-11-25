"use client"

import { Champ } from "@/components/app/champ"
import { useFormulaire } from "@/components/app/formulaire"
import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { changerMotDePasse } from "@/lib/actions/compte"

export function FormulaireMotDePasse() {
  const { surEnvoi, enCours, erreurs } = useFormulaire(changerMotDePasse)
  const d = useDico()
  return (
    <form onSubmit={surEnvoi} className="grid max-w-md gap-5 rounded-[22px] verre-carte p-6">
      <Champ nom="current_password" libelle={d.mdp.actuel} erreurs={erreurs}>
        <Input id="current_password" name="current_password" type="password" autoComplete="current-password" required />
      </Champ>
      <Champ nom="new_password" libelle={d.mdp.nouveau} aide={d.mdp.aide} erreurs={erreurs}>
        <Input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={8} />
      </Champ>
      <Champ nom="new_password2" libelle={d.mdp.confirmerNouveau} erreurs={erreurs}>
        <Input id="new_password2" name="new_password2" type="password" autoComplete="new-password" required />
      </Champ>
      <Button type="submit" size="lg" disabled={enCours} className="justify-self-start">
        {enCours && <Spinner />} {d.mdp.changer}
      </Button>
    </form>
  )
}
