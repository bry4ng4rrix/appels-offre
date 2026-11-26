"use client"

import { AnimatePresence, motion } from "motion/react"
import { CircleAlertIcon, CircleCheckIcon, EyeIcon, EyeOffIcon } from "lucide-react"
import Link from "next/link"
import { useState } from "react"

import { Champ } from "@/components/app/champ"
import { useEnvoi } from "@/components/app/formulaire"
import { useDico } from "@/components/app/traductions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group"
import { Spinner } from "@/components/ui/spinner"
import { connexion, inscription, motDePasseOublie } from "@/lib/actions/compte"
import type { Resultat } from "@/lib/api/types"

function MotDePasse({ id, nom, autoComplete }: { id: string; nom: string; autoComplete: string }) {
  const tx = useDico()
  const [visible, setVisible] = useState(false)
  return (
    <InputGroup>
      <InputGroupInput id={id} name={nom} type={visible ? "text" : "password"} autoComplete={autoComplete} required />
      <InputGroupAddon align="inline-end">
        <InputGroupButton size="icon-xs" aria-label={visible ? tx.entree.masquer : tx.entree.afficher} onClick={() => setVisible((v) => !v)}>
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
  )
}

/** Message de resultat sous le titre : erreur generale ou confirmation. */
function Annonce({ etat }: { etat: Resultat | null }) {
  return (
    <AnimatePresence>
      {etat && (etat.ok ? etat.message : etat.erreur) && (
        <motion.p
          key={etat.ok ? etat.message : etat.erreur}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          role={etat.ok ? "status" : "alert"}
          className={`flex gap-2 rounded-2xl px-4 py-3 text-sm ${etat.ok ? "bg-lointaine/10 text-lointaine" : "bg-urgent/10 text-urgent"}`}
        >
          {etat.ok ? <CircleCheckIcon className="mt-0.5 size-4 shrink-0" /> : <CircleAlertIcon className="mt-0.5 size-4 shrink-0" />}
          {etat.ok ? etat.message : etat.erreur}
        </motion.p>
      )}
    </AnimatePresence>
  )
}

function Titre({ titre, sous }: { titre: string; sous: React.ReactNode }) {
  return (
    <div>
      <h1 className="text-3xl font-normal tracking-tight">{titre}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{sous}</p>
    </div>
  )
}

export function FormulaireConnexion({ suivant, expiree }: { suivant?: string; expiree?: boolean }) {
  const tx = useDico()
  const { etat, surEnvoi, enCours, erreurs } = useEnvoi(connexion)
  return (
    <form onSubmit={surEnvoi} className="grid gap-6">
      <Titre
        titre={tx.entree.seConnecter}
        sous={
          <>
            {tx.entree.pasDeCompte}{" "}
            <Link href="/inscription" className="font-medium text-foreground underline underline-offset-4">
              {tx.entree.creerGratuit}
            </Link>
          </>
        }
      />
      {expiree && !etat && <Annonce etat={{ ok: false, erreur: tx.entree.expiree }} />}
      <Annonce etat={etat && !etat.ok && !Object.keys(etat.champs ?? {}).length ? etat : null} />
      <input type="hidden" name="suivant" value={suivant ?? ""} />
      <Champ nom="email" libelle={tx.entree.email} erreurs={erreurs}>
        <Input id="email" name="email" type="email" autoComplete="email" required autoFocus />
      </Champ>
      <Champ
        nom="password"
        libelle={
          <span className="flex w-full justify-between">
            {tx.entree.motDePasse}
            <Link href="/mot-de-passe-oublie" className="-my-2.5 py-2.5 font-normal text-muted-foreground hover:text-foreground">
              {tx.entree.oublie}
            </Link>
          </span>
        }
        erreurs={erreurs}
      >
        <MotDePasse id="password" nom="password" autoComplete="current-password" />
      </Champ>
      <Button type="submit" size="lg" disabled={enCours} className="h-12 text-base">
        {enCours && <Spinner />} {tx.entree.seConnecter}
      </Button>
    </form>
  )
}

export function FormulaireInscription() {
  const tx = useDico()
  const { etat, surEnvoi, enCours, erreurs } = useEnvoi(inscription)
  return (
    <form onSubmit={surEnvoi} className="grid gap-6">
      <Titre
        titre={tx.entree.creerCompte}
        sous={
          <>
            {tx.entree.gratuit}{" "}
            <Link href="/connexion" className="font-medium text-foreground underline underline-offset-4">
              {tx.entree.seConnecter}
            </Link>
          </>
        }
      />
      <Annonce etat={etat && !etat.ok && !Object.keys(etat.champs ?? {}).length ? etat : null} />
      <Champ nom="email" libelle={tx.entree.email} erreurs={erreurs}>
        <Input id="email" name="email" type="email" autoComplete="email" required autoFocus />
      </Champ>
      <Champ nom="password" libelle={tx.entree.motDePasse} aide={tx.mdp.aide} erreurs={erreurs}>
        <MotDePasse id="password" nom="password" autoComplete="new-password" />
      </Champ>
      <Champ nom="password2" libelle={tx.entree.confirmer} erreurs={erreurs}>
        <MotDePasse id="password2" nom="password2" autoComplete="new-password" />
      </Champ>
      <Button type="submit" size="lg" disabled={enCours} className="h-12 text-base">
        {enCours && <Spinner />} {tx.entree.creerMonCompte}
      </Button>
    </form>
  )
}

export function FormulaireOubli() {
  const tx = useDico()
  const { etat, surEnvoi, enCours, erreurs } = useEnvoi(motDePasseOublie)
  return (
    <form onSubmit={surEnvoi} className="grid gap-6">
      <Titre titre={tx.entree.oubliTitre} sous={tx.entree.oubliTexte} />
      <Annonce etat={etat} />
      <Champ nom="email" libelle={tx.entree.email} erreurs={erreurs}>
        <Input id="email" name="email" type="email" autoComplete="email" required autoFocus />
      </Champ>
      <Button type="submit" size="lg" disabled={enCours} className="h-12 text-base">
        {enCours && <Spinner />} {tx.entree.envoyerLien}
      </Button>
      <Link href="/connexion" className="text-center text-sm text-muted-foreground hover:text-foreground">
        {tx.entree.retourConnexion}
      </Link>
    </form>
  )
}
