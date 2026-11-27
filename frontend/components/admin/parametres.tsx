"use client"

import { CheckIcon, MailCheckIcon, PencilIcon, PlusIcon, SearchIcon, Trash2Icon, XIcon } from "lucide-react"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { Champ } from "@/components/app/champ"
import { useFormulaire } from "@/components/app/formulaire"
import { useDico } from "@/components/app/traductions"
import { Statut } from "@/components/app/statut"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import {
  ajouterAuCatalogue,
  basculerDansCatalogue,
  reglerCollecte,
  reglerEmail,
  reglerPertinence,
  renommerDansCatalogue,
  retirerDuCatalogue,
  testerEmail,
} from "@/lib/actions/admin"
import type { ElementCatalogue, Parametres } from "@/lib/api/types"
import { formateurs } from "@/lib/format"
import { f, libelle } from "@/lib/i18n"

function Carte({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-5 rounded-[22px] verre-carte p-6 ">{children}</div>
}

export function FormCollecte({ collecte }: { collecte: Parametres["collecte"] }) {
  const tx = useDico()
  const { dateEtHeure } = formateurs(tx.locale)
  const { surEnvoi, enCours, erreurs } = useFormulaire(reglerCollecte)
  const [weekend, setWeekend] = useState(collecte.pause_weekend)
  return (
    <form onSubmit={surEnvoi}>
      <Carte>
        <div className="grid gap-5 sm:grid-cols-2">
          <Champ nom="intervalle_collecte" libelle={tx.params.intervalle} aide={tx.params.intervalleAide} erreurs={erreurs}>
            <Input id="intervalle_collecte" name="intervalle_collecte" type="number" min={1} max={24} defaultValue={collecte.intervalle_collecte} required />
          </Champ>
          <Champ nom="heure_nuit" libelle={tx.params.nuit} aide={tx.params.nuitAide} erreurs={erreurs}>
            <Input id="heure_nuit" name="heure_nuit" type="time" defaultValue={collecte.heure_nuit} />
          </Champ>
        </div>
        <div className="flex items-center justify-between gap-4 rounded-2xl bg-muted p-3.5">
          <div className="grid gap-1">
            <Label htmlFor="pause_weekend">{tx.params.weekend}</Label>
            <p className="text-xs text-muted-foreground">{tx.params.weekendAide}</p>
          </div>
          <Switch id="pause_weekend" checked={weekend} onCheckedChange={setWeekend} />
          <input type="hidden" name="pause_weekend" value={weekend ? "on" : ""} />
        </div>
        <dl className="grid gap-2 rounded-2xl bg-muted p-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">{tx.params.prochaine}</dt>
            <dd>{collecte.automatismes_suspendus ? tx.params.suspendue : dateEtHeure(collecte.prochaine)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">{tx.params.derniereAuto}</dt>
            <dd>{collecte.derniere_auto ? `${libelle(tx.taches.statuts, collecte.derniere_auto.statut, collecte.derniere_auto.statut_libelle)}, ${dateEtHeure(collecte.derniere_auto.debut)}` : "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">{tx.params.derniereNuit}</dt>
            <dd>{collecte.derniere_nuit ? `${libelle(tx.taches.statuts, collecte.derniere_nuit.statut, collecte.derniere_nuit.statut_libelle)}, ${dateEtHeure(collecte.derniere_nuit.debut)}` : "—"}</dd>
          </div>
        </dl>
        <Button type="submit" size="lg" disabled={enCours} className="justify-self-start">
          {enCours && <Spinner />} {tx.commun.enregistrer}
        </Button>
      </Carte>
    </form>
  )
}

export function FormEmail({ email }: { email: Parametres["email"] }) {
  const tx = useDico()
  const { surEnvoi, enCours, erreurs } = useFormulaire(reglerEmail)
  const [securite, setSecurite] = useState(email.smtp_securite)
  const [test, demarrerTest] = useTransition()
  const items = email.securites.map((s) => ({ value: s.code, label: s.libelle }))
  return (
    <form onSubmit={surEnvoi}>
      <Carte>
        {email.source !== "ecran" && (
          <p className="rounded-2xl bg-accent px-4 py-3 text-sm text-accent-foreground">
            {email.source === "env"
              ? tx.params.sourceEnv
              : tx.params.sourceConsole}
          </p>
        )}
        <div className="grid gap-5 sm:grid-cols-2">
          <Champ nom="smtp_hote" libelle={tx.params.smtp} erreurs={erreurs}>
            <Input id="smtp_hote" name="smtp_hote" defaultValue={email.smtp_hote} placeholder="smtp.exemple.org" />
          </Champ>
          <Champ nom="smtp_port" libelle={tx.params.port} erreurs={erreurs}>
            <Input id="smtp_port" name="smtp_port" type="number" defaultValue={email.smtp_port} placeholder="587" />
          </Champ>
          <Champ nom="smtp_securite" libelle={tx.params.securite} erreurs={erreurs}>
            <Select items={items} value={securite} onValueChange={(v) => setSecurite(String(v ?? ""))}>
              <SelectTrigger id="smtp_securite" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {items.map((i) => (
                  <SelectItem key={i.value} value={i.value}>
                    {i.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <input type="hidden" name="smtp_securite" value={securite} />
          </Champ>
          <Champ nom="smtp_utilisateur" libelle={tx.params.utilisateur} erreurs={erreurs}>
            <Input id="smtp_utilisateur" name="smtp_utilisateur" defaultValue={email.smtp_utilisateur} autoComplete="off" />
          </Champ>
          <Champ
            nom="smtp_mot_de_passe"
            libelle={tx.params.motDePasse}
            aide={email.mot_de_passe_enregistre ? tx.params.mdpEnregistre : undefined}
            erreurs={erreurs}
            className="sm:col-span-2"
          >
            <Input id="smtp_mot_de_passe" name="smtp_mot_de_passe" type="password" autoComplete="new-password" />
          </Champ>
          <Champ nom="destinataires" libelle={tx.params.destinataires} aide={tx.params.destinatairesAide} erreurs={erreurs} className="sm:col-span-2">
            <Textarea id="destinataires" name="destinataires" defaultValue={email.destinataires.join("\n")} rows={3} />
          </Champ>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="lg" disabled={enCours}>
            {enCours && <Spinner />} {tx.commun.enregistrer}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="lg"
            disabled={test}
            onClick={() =>
              demarrerTest(async () => {
                const r = await testerEmail()
                if (r.ok) toast.success(r.message)
                else toast.error(r.erreur)
              })
            }
          >
            {test ? <Spinner /> : <MailCheckIcon />} {tx.params.tester}
          </Button>
        </div>
      </Carte>
    </form>
  )
}

export function FormPertinence({ criteres }: { criteres: Parametres["pertinence"] }) {
  const tx = useDico()
  const { surEnvoi, enCours } = useFormulaire(reglerPertinence)
  const [poids, setPoids] = useState(() => Object.fromEntries(criteres.map((c) => [c.code, c.poids])))
  const total = Object.values(poids).reduce((a, b) => a + b, 0) || 1
  return (
    <form onSubmit={surEnvoi}>
      <Carte>
        <p className="text-sm text-muted-foreground">
          {tx.params.poidsTexte}
        </p>
        <div className="grid gap-6">
          {criteres.map((c) => (
            <div key={c.code} className="grid gap-2">
              <div className="flex items-baseline justify-between">
                <label htmlFor={`poids-${c.code}`} className="text-sm">
                  {c.libelle}
                </label>
                <span className="text-sm text-muted-foreground tabular-nums">
                  {poids[c.code]} <span className="text-ambre">({Math.round((poids[c.code] / total) * 100)} %)</span>
                </span>
              </div>
              <Slider id={`poids-${c.code}`} value={[poids[c.code]]} min={0} max={100} step={1} onValueChange={(v) => setPoids((p) => ({ ...p, [c.code]: Array.isArray(v) ? v[0] : v }))} />
              <input type="hidden" name={c.code} value={poids[c.code]} />
            </div>
          ))}
        </div>
        <Button type="submit" size="lg" disabled={enCours} className="justify-self-start">
          {enCours && <Spinner />} {tx.params.enregistrerPoids}
        </Button>
      </Carte>
    </form>
  )
}

function LigneCatalogue({ catalogue, element }: { catalogue: "secteurs" | "pays"; element: ElementCatalogue }) {
  const tx = useDico()
  const [edition, setEdition] = useState(false)
  const [nom, setNom] = useState(element.nom)
  const [enCours, demarrer] = useTransition()
  const agir = (appel: () => Promise<{ ok: boolean; message?: string; erreur?: string }>, apres?: () => void) =>
    demarrer(async () => {
      const r = await appel()
      if (r.ok) {
        toast.success(r.message ?? tx.commun.enregistre)
        apres?.()
      } else toast.error(r.erreur)
    })
  return (
    <li className="flex flex-wrap items-center gap-3 px-4 py-2.5">
      {edition ? (
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            agir(() => renommerDansCatalogue(catalogue, element.id, nom.trim()), () => setEdition(false))
          }}
        >
          <Input value={nom} onChange={(e) => setNom(e.target.value)} autoFocus aria-label={tx.params.nouveauNom} className="h-9" />
          <Button type="submit" size="icon" aria-label={tx.params.enregistrerNom} disabled={enCours}>
            <CheckIcon />
          </Button>
          <Button type="button" size="icon" variant="ghost" aria-label={tx.commun.annuler} onClick={() => setEdition(false)}>
            <XIcon />
          </Button>
        </form>
      ) : (
        <>
          <span className="min-w-40 flex-1 text-sm">{element.nom}</span>
          <span className="text-xs text-muted-foreground tabular-nums">{f(tx.params.nOffres, { n: element.nombre_offres })}</span>
          <Switch
            checked={element.actif}
            disabled={enCours}
            aria-label={f(element.actif ? tx.params.masquer : tx.params.proposer, { nom: element.nom })}
            onCheckedChange={() => agir(() => basculerDansCatalogue(catalogue, element.id))}
          />
          <Button size="icon-sm" variant="ghost" aria-label={f(tx.params.renommer, { nom: element.nom })} onClick={() => setEdition(true)}>
            <PencilIcon />
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label={f(tx.params.retirer, { nom: element.nom })} disabled={enCours} onClick={() => agir(() => retirerDuCatalogue(catalogue, element.id))}>
            <Trash2Icon />
          </Button>
        </>
      )}
    </li>
  )
}

/** Secteurs ou pays proposes dans les filtres et le profil. */
export function Catalogue({ catalogue, elements }: { catalogue: "secteurs" | "pays"; elements: ElementCatalogue[] }) {
  const tx = useDico()
  const [filtre, setFiltre] = useState("")
  const [nouveau, setNouveau] = useState("")
  const [enCours, demarrer] = useTransition()
  const visibles = elements.filter((e) => e.nom.toLowerCase().includes(filtre.toLowerCase()))
  const actifs = elements.filter((e) => e.actif).length
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-2">
        <InputGroup className="max-w-xs rounded-full">
          <InputGroupAddon>
            <SearchIcon />
          </InputGroupAddon>
          <InputGroupInput value={filtre} onChange={(e) => setFiltre(e.target.value)} placeholder={tx.params.filtrer} aria-label={tx.params.filtrerListe} />
        </InputGroup>
        <form
          className="ms-auto flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            demarrer(async () => {
              const r = await ajouterAuCatalogue(catalogue, nouveau.trim())
              if (r.ok) {
                toast.success(r.message ?? tx.params.ajoute)
                setNouveau("")
              } else toast.error(r.erreur)
            })
          }}
        >
          <Input value={nouveau} onChange={(e) => setNouveau(e.target.value)} placeholder={catalogue === "pays" ? tx.params.nouveauPays : tx.params.nouveauSecteur} required aria-label={tx.params.nomAjouter} />
          <Button type="submit" disabled={enCours}>
            {enCours ? <Spinner /> : <PlusIcon />} {tx.params.ajouter}
          </Button>
        </form>
      </div>
      <p className="text-sm text-muted-foreground">
        <Statut ton="succes">{f(tx.params.proposes, { n: actifs })}</Statut> {f(tx.params.sur, { n: elements.length })} {tx.params.masqueAide}
      </p>
      <ul className="max-h-[36rem] divide-y overflow-y-auto rounded-[22px] verre-carte ">
        {visibles.map((e) => (
          <LigneCatalogue key={e.id} catalogue={catalogue} element={e} />
        ))}
        {visibles.length === 0 && <li className="p-4 text-sm text-muted-foreground">{tx.params.rien}</li>}
      </ul>
    </div>
  )
}
