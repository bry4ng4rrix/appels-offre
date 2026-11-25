"use client"

import { AnimatePresence, motion } from "motion/react"
import { CheckIcon, CircleIcon, CopyIcon, KeyRoundIcon, PauseIcon, PlayIcon, PlusIcon, SquareIcon, Trash2Icon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState, useTransition } from "react"
import { toast } from "sonner"

import { Statut, type TonStatut } from "@/components/app/statut"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { agirSurTache, agirSurToutes, creerCle, lancerTache, revoquerCle } from "@/lib/actions/admin"
import type { Cle, Resultat, Tache, TacheDetail, Taches } from "@/lib/api/types"
import { dateEtHeure } from "@/lib/format"
import { cn } from "@/lib/utils"

const TONS: Record<string, TonStatut> = {
  en_cours: "info",
  terminee: "succes",
  echec: "erreur",
  interrompue: "attente",
  suspendue: "attente",
  annulee: "neutre",
}

export function tonTache(statut: string): TonStatut {
  return TONS[statut] ?? "neutre"
}

function duree(s: number) {
  if (s < 60) return `${s} s`
  const m = Math.floor(s / 60)
  return m < 60 ? `${m} min ${s % 60} s` : `${Math.floor(m / 60)} h ${m % 60} min`
}

/** Un bouton qui lance une action serveur et annonce son resultat. */
function Action({
  faire,
  children,
  ...props
}: { faire: () => Promise<Resultat> } & Omit<React.ComponentProps<typeof Button>, "onClick">) {
  const [enCours, demarrer] = useTransition()
  return (
    <Button
      {...props}
      disabled={enCours || props.disabled}
      onClick={() =>
        demarrer(async () => {
          const r = await faire()
          if (r.ok) toast.success(r.message ?? "Fait.")
          else (r.statut === 409 ? toast.info : toast.error)(r.erreur)
        })
      }
    >
      {enCours && <Spinner />}
      {children}
    </Button>
  )
}

function Phases({ tache }: { tache: Tache }) {
  return (
    <ol className="flex flex-wrap gap-2">
      {tache.phases.map((p, i) => (
        <li
          key={i}
          className={cn(
            "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs",
            p.etat === "faite" && "bg-lointaine/10 text-lointaine",
            p.etat === "active" && "bg-ambre text-ambre-foreground",
            p.etat === "a_venir" && "bg-muted text-muted-foreground",
          )}
        >
          {p.etat === "faite" ? <CheckIcon className="size-3" /> : p.etat === "active" ? <Spinner className="size-3" /> : <CircleIcon className="size-3" />}
          {p.libelle}
        </li>
      ))}
    </ol>
  )
}

/** Le tableau de bord des taches, rafraichi en direct tant qu'une tache tourne. */
export function TableauTaches({ initial }: { initial: Taches }) {
  const [t, setT] = useState(initial)
  const [journal, setJournal] = useState<string>("")
  const router = useRouter()
  const avant = useRef(initial.active?.id ?? null)
  const fond = useRef<HTMLPreElement>(null)

  // Nouvelles donnees du serveur (apres une action) : elles remplacent l'etat local.
  const [initialVu, setInitialVu] = useState(initial)
  if (initial !== initialVu) {
    setInitialVu(initial)
    setT(initial)
  }

  useEffect(() => {
    let arret = false
    async function lire() {
      const r = await fetch("/bff/admin/taches").catch(() => null)
      if (!r?.ok || arret) return
      const n = (await r.json()) as Taches
      setT(n)
      if (n.active) {
        const d = await fetch(`/bff/admin/taches/${n.active.id}`).then((x) => (x.ok ? (x.json() as Promise<TacheDetail>) : null)).catch(() => null)
        if (d && !arret) setJournal(d.journal)
      }
      // La tache vient de finir : statistiques et sources ont change.
      if (avant.current && !n.active) router.refresh()
      avant.current = n.active?.id ?? null
    }
    const id = setInterval(lire, t.active ? 2000 : 15000)
    if (t.active) lire()
    return () => {
      arret = true
      clearInterval(id)
    }
  }, [t.active, router])

  useEffect(() => {
    fond.current?.scrollTo({ top: fond.current.scrollHeight })
  }, [journal])

  const a = t.active
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Action faire={() => lancerTache("tout")} size="lg" disabled={!!a}>
          <PlayIcon /> Tout lancer
        </Action>
        {t.types
          .filter((x) => x.nom !== "tout")
          .map((x) => (
            <Action key={x.nom} faire={() => lancerTache(x.nom)} variant="secondary" size="lg" disabled={!!a} title={x.phases.join(", ")}>
              {x.libelle}
            </Action>
          ))}
        <div className="ml-auto flex gap-2">
          <Action faire={() => agirSurToutes("suspendre")} variant="ghost">
            <PauseIcon /> Tout suspendre
          </Action>
          <Action faire={() => agirSurToutes("reprendre")} variant="ghost">
            <PlayIcon /> Tout reprendre
          </Action>
        </div>
      </div>

      {t.automatismes_suspendus && (
        <p className="rounded-2xl bg-proche/10 px-4 py-3 text-sm text-proche">
          Les collectes automatiques sont suspendues. « Tout reprendre » les relance.
        </p>
      )}

      <AnimatePresence mode="wait">
        {a ? (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="grid gap-4 rounded-[22px] verre-carte p-5 "
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="flex items-center gap-2 text-lg">
                  <span className="size-2 rounded-full bg-ambre battement" /> {a.libelle}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {a.etape}
                  {a.total > 0 && ` (${a.courant} sur ${a.total})`}, depuis {duree(a.duree_secondes)}
                </p>
              </div>
              <div className="flex gap-2">
                <Action faire={() => agirSurTache(a.id, "suspendre")} variant="secondary">
                  <PauseIcon /> Suspendre
                </Action>
                <Action faire={() => agirSurTache(a.id, "annuler")} variant="destructive">
                  <SquareIcon /> Annuler
                </Action>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <motion.div className="degrade h-full rounded-full" animate={{ width: `${a.pourcentage}%` }} transition={{ ease: "easeOut" }} />
              </div>
              <span className="w-12 text-right text-2xl font-light tabular-nums">{a.pourcentage}%</span>
            </div>
            <Phases tache={a} />
            {journal && (
              <pre ref={fond} className="max-h-64 overflow-auto rounded-2xl bg-primary p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap text-primary-foreground/85">
                {journal}
              </pre>
            )}
          </motion.div>
        ) : (
          <motion.p key="calme" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-[22px] verre-carte p-5 text-sm text-muted-foreground ">
            Aucune tâche en cours. La collecte automatique passe toutes les {t.intervalle_collecte} heures sur {t.nb_sources} sources.
          </motion.p>
        )}
      </AnimatePresence>

      {t.a_reprendre.length > 0 && (
        <div className="grid gap-2">
          <h3 className="font-medium">À reprendre</h3>
          {t.a_reprendre.map((x) => (
            <div key={x.id} className="flex flex-wrap items-center justify-between gap-3 rounded-[22px] verre-carte p-4 ">
              <div>
                <p className="text-sm">{x.libelle}</p>
                <p className="text-xs text-muted-foreground">
                  {x.statut_libelle} à l&apos;étape « {x.etape} », {x.pourcentage} %
                </p>
              </div>
              <div className="flex gap-2">
                <Action faire={() => agirSurTache(x.id, "annuler")} variant="ghost">
                  Abandonner
                </Action>
                <Action faire={() => agirSurTache(x.id, "reprendre")} disabled={!!a}>
                  <PlayIcon /> Reprendre
                </Action>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-2">
        <h3 className="font-medium">Historique</h3>
        <ul className="divide-y rounded-[22px] verre-carte ">
          {t.historique.map((x) => (
            <li key={x.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <span className="min-w-40 flex-1">
                {x.libelle}
                {x.automatique && <span className="ml-2 text-xs text-muted-foreground">automatique</span>}
              </span>
              <Statut ton={tonTache(x.statut)}>{x.statut_libelle}</Statut>
              <span className="w-24 text-right text-xs text-muted-foreground tabular-nums">{duree(x.duree_secondes)}</span>
              <span className="w-40 text-right text-xs text-muted-foreground">{dateEtHeure(x.debut)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

/** Cles de l'API machine : le jeton n'est montre qu'une fois, a la creation. */
export function Cles({ cles }: { cles: Cle[] }) {
  const [nom, setNom] = useState("")
  const [jeton, setJeton] = useState<string | null>(null)
  const [enCours, demarrer] = useTransition()
  return (
    <div className="grid gap-3">
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          demarrer(async () => {
            const r = await creerCle(nom.trim())
            if (r.ok && r.donnees) {
              setJeton(r.donnees.jeton)
              setNom("")
            } else if (!r.ok) toast.error(r.erreur)
          })
        }}
      >
        <Input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom de la clé, par exemple : script de rapport" className="max-w-sm" required aria-label="Nom de la nouvelle clé" />
        <Button type="submit" disabled={enCours}>
          {enCours ? <Spinner /> : <PlusIcon />} Créer une clé
        </Button>
      </form>
      <Dialog open={!!jeton} onOpenChange={(o) => !o && setJeton(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Clé créée</DialogTitle>
            <DialogDescription>Copiez-la maintenant : elle ne sera plus jamais affichée.</DialogDescription>
          </DialogHeader>
          <code className="rounded-2xl bg-muted p-4 font-mono text-sm break-all">{jeton}</code>
          <DialogFooter>
            <Button onClick={() => jeton && navigator.clipboard.writeText(jeton).then(() => toast.success("Clé copiée."))}>
              <CopyIcon /> Copier la clé
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ul className="divide-y rounded-[22px] verre-carte ">
        {cles.length === 0 && <li className="p-4 text-sm text-muted-foreground">Aucune clé pour le moment.</li>}
        {cles.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
            <KeyRoundIcon className="size-4 text-muted-foreground" />
            <span className="min-w-40 flex-1">{c.nom}</span>
            <Statut ton={c.active ? "succes" : "neutre"}>{c.active ? "Active" : "Révoquée"}</Statut>
            <span className="text-xs text-muted-foreground">
              {c.derniere_utilisation ? `utilisée le ${dateEtHeure(c.derniere_utilisation)}` : "jamais utilisée"}
            </span>
            {c.active && (
              <Action faire={() => revoquerCle(c.id)} variant="ghost" size="sm">
                <Trash2Icon /> Révoquer
              </Action>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
