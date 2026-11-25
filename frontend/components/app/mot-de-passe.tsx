"use client"

import { Champ } from "@/components/app/champ"
import { useFormulaire } from "@/components/app/formulaire"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { changerMotDePasse } from "@/lib/actions/compte"

export function FormulaireMotDePasse() {
  const { soumettre, enCours, erreurs } = useFormulaire(changerMotDePasse)
  return (
    <form action={soumettre} className="grid max-w-md gap-5 rounded-[22px] bg-card ring-1 ring-border/70 p-6">
      <Champ nom="current_password" libelle="Mot de passe actuel" erreurs={erreurs}>
        <Input id="current_password" name="current_password" type="password" autoComplete="current-password" required />
      </Champ>
      <Champ nom="new_password" libelle="Nouveau mot de passe" aide="8 caractères au moins, pas uniquement des chiffres." erreurs={erreurs}>
        <Input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={8} />
      </Champ>
      <Champ nom="new_password2" libelle="Confirmer le nouveau mot de passe" erreurs={erreurs}>
        <Input id="new_password2" name="new_password2" type="password" autoComplete="new-password" required />
      </Champ>
      <Button type="submit" size="lg" disabled={enCours} className="justify-self-start">
        {enCours && <Spinner />} Changer le mot de passe
      </Button>
    </form>
  )
}
