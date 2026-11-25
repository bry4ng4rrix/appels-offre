"use client"

import { AnimatePresence, motion } from "motion/react"
import { DownloadIcon, FileTextIcon, ImageUpIcon, Trash2Icon, UploadIcon } from "lucide-react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useState, useTransition } from "react"
import { toast } from "sonner"

import { Champ } from "@/components/app/champ"
import { useFormulaire } from "@/components/app/formulaire"
import { ChoixMultiples, ChoixUnique, Puces, type Option } from "@/components/profil/selections"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { deposerCv, enregistrerSection, supprimerCv, type Section } from "@/lib/actions/profil"
import type { Choix, Profil, Reference } from "@/lib/api/types"
import { date } from "@/lib/format"

const ids = (l: { id: number; nom: string }[]): Option[] => l.map((x) => ({ valeur: String(x.id), libelle: x.nom }))
const codes = (l: Choix[]): Option[] => l.map((x) => ({ valeur: x.code, libelle: x.libelle }))

function Enregistrer({ enCours }: { enCours: boolean }) {
  return (
    <div className="sticky bottom-4 z-10 mt-2 flex justify-end">
      <Button type="submit" size="lg" disabled={enCours} className="h-11 px-5 shadow-lg">
        {enCours && <Spinner />} Enregistrer
      </Button>
    </div>
  )
}

function Bloc({ titre, description, children }: { titre: string; description?: string; children: React.ReactNode }) {
  return (
    <fieldset className="grid gap-5 rounded-[22px] verre-carte p-6 sm:grid-cols-[14rem_1fr] sm:gap-8">
      <div>
        <legend className="font-medium">{titre}</legend>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="grid gap-5 sm:grid-cols-2">{children}</div>
    </fieldset>
  )
}

/** Liste deroulante courte, envoyee par un champ cache (une valeur vide = non precise). */
function ListeCourte({ id, nom, options, valeur }: { id: string; nom: string; options: Choix[]; valeur?: string | null }) {
  const [v, setV] = useState(valeur ?? "")
  const items = [{ value: "", label: "Non précisé" }, ...options.map((o) => ({ value: o.code, label: o.libelle }))]
  return (
    <>
      <Select items={items} value={v} onValueChange={(x) => setV(String(x ?? ""))}>
        <SelectTrigger id={id} className="w-full bg-card">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {items.map((i) => (
            <SelectItem key={i.value || "vide"} value={i.value}>
              {i.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <input type="hidden" name={nom} value={v} />
    </>
  )
}

function useSection(section: Section) {
  return useFormulaire(enregistrerSection.bind(null, section))
}

function Perso({ profil, choix }: { profil: Profil; choix: Reference }) {
  const { surEnvoi, enCours, erreurs } = useSection("perso")
  const p = profil.perso
  const [apercu, setApercu] = useState<string | null>(null)
  const [retirer, setRetirer] = useState(false)
  const photo = retirer ? null : (apercu ?? (profil.photo ? "/bff/profil/photo" : null))
  return (
    <form onSubmit={surEnvoi} className="grid gap-5">
      <Bloc titre="Photo" description="PNG, JPEG ou WebP, 2 Mo au plus.">
        <div className="flex items-center gap-5 sm:col-span-2">
          <Avatar className="size-20 ring-4 ring-accent">
            {photo && <AvatarImage src={photo} alt="Votre photo" className="object-cover" />}
            <AvatarFallback className="bg-primary text-2xl font-semibold text-primary-foreground">
              {(p.first_name || "?").charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="grid gap-2">
            <Label htmlFor="photo" className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm font-medium hover:bg-muted">
              <ImageUpIcon className="size-4" /> Choisir une photo
            </Label>
            <input
              id="photo"
              name="photo"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0]
                setApercu(f ? URL.createObjectURL(f) : null)
                setRetirer(false)
              }}
            />
            {profil.photo && (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <Checkbox checked={retirer} onCheckedChange={(v) => setRetirer(!!v)} />
                Retirer la photo actuelle
              </label>
            )}
            <input type="hidden" name="supprimer_photo" value={retirer ? "on" : ""} />
          </div>
        </div>
      </Bloc>
      <Bloc titre="Identité">
        <Champ nom="first_name" libelle="Prénom" erreurs={erreurs}>
          <Input id="first_name" name="first_name" defaultValue={p.first_name} autoComplete="given-name" />
        </Champ>
        <Champ nom="last_name" libelle="Nom" erreurs={erreurs}>
          <Input id="last_name" name="last_name" defaultValue={p.last_name} autoComplete="family-name" />
        </Champ>
        <Champ nom="telephone" libelle="Téléphone" erreurs={erreurs}>
          <Input id="telephone" name="telephone" type="tel" defaultValue={p.telephone} autoComplete="tel" />
        </Champ>
        <Champ nom="date_naissance" libelle="Date de naissance" erreurs={erreurs}>
          <Input id="date_naissance" name="date_naissance" type="date" defaultValue={p.date_naissance ?? ""} />
        </Champ>
      </Bloc>
      <Bloc titre="Adresse" description="Sert à proposer les offres proches de chez vous.">
        <Champ nom="adresse" libelle="Adresse" erreurs={erreurs} className="sm:col-span-2">
          <Input id="adresse" name="adresse" defaultValue={p.adresse} autoComplete="street-address" />
        </Champ>
        <Champ nom="ville" libelle="Ville" erreurs={erreurs}>
          <Input id="ville" name="ville" defaultValue={p.ville} autoComplete="address-level2" />
        </Champ>
        <Champ nom="region" libelle="Région" erreurs={erreurs}>
          <Input id="region" name="region" defaultValue={p.region} autoComplete="address-level1" />
        </Champ>
        <Champ nom="code_postal" libelle="Code postal" erreurs={erreurs}>
          <Input id="code_postal" name="code_postal" defaultValue={p.code_postal} autoComplete="postal-code" />
        </Champ>
        <Champ nom="pays" libelle="Pays" erreurs={erreurs}>
          <ChoixUnique id="pays" nom="pays" options={ids(choix.profil.pays)} valeur={p.pays ? String(p.pays) : null} placeholder="Choisir un pays" />
        </Champ>
      </Bloc>
      <Enregistrer enCours={enCours} />
    </form>
  )
}

function Pro({ profil, choix }: { profil: Profil; choix: Reference }) {
  const { surEnvoi, enCours, erreurs } = useSection("pro")
  const p = profil.pro
  const r = choix.profil
  return (
    <form onSubmit={surEnvoi} className="grid gap-5">
      <Bloc titre="Votre métier" description="Ce que vous faites, en quelques mots.">
        <Champ nom="titre" libelle="Titre" aide="Par exemple : ingénieur hydraulicien, consultant en évaluation." erreurs={erreurs} className="sm:col-span-2">
          <Input id="titre" name="titre" defaultValue={p.titre} />
        </Champ>
        <Champ nom="description" libelle="Présentation" erreurs={erreurs} className="sm:col-span-2">
          <Textarea id="description" name="description" defaultValue={p.description} rows={5} />
        </Champ>
        <Champ nom="annees_experience" libelle="Années d'expérience" erreurs={erreurs}>
          <Input id="annees_experience" name="annees_experience" type="number" min={0} max={60} defaultValue={p.annees_experience ?? ""} />
        </Champ>
        <Champ nom="niveau_etudes" libelle="Niveau d'études" erreurs={erreurs}>
          <ListeCourte id="niveau_etudes" nom="niveau_etudes" options={r.niveaux_etudes} valeur={p.niveau_etudes} />
        </Champ>
      </Bloc>
      <Bloc titre="Ce que vous cherchez">
        <Champ nom="type_contrat" libelle="Type de contrat" erreurs={erreurs}>
          <ListeCourte id="type_contrat" nom="type_contrat" options={r.types_contrat} valeur={p.type_contrat} />
        </Champ>
        <Champ nom="disponibilite" libelle="Disponibilité" erreurs={erreurs}>
          <ListeCourte id="disponibilite" nom="disponibilite" options={r.disponibilites} valeur={p.disponibilite} />
        </Champ>
        <Champ nom="mode_travail" libelle="Mode de travail" erreurs={erreurs}>
          <ListeCourte id="mode_travail" nom="mode_travail" options={r.modes_travail} valeur={p.mode_travail} />
        </Champ>
      </Bloc>
      <Enregistrer enCours={enCours} />
    </form>
  )
}

function Domaines({ profil, choix }: { profil: Profil; choix: Reference }) {
  const { surEnvoi, enCours, erreurs } = useSection("domaines")
  const d = profil.domaines
  return (
    <form onSubmit={surEnvoi} className="grid gap-5">
      <Bloc titre="Vos domaines" description="Le score des suggestions compare ces choix au secteur et à la catégorie de chaque offre.">
        <Champ nom="secteurs" libelle="Secteurs" erreurs={erreurs} className="sm:col-span-2">
          <ChoixMultiples id="secteurs" nom="secteurs" options={ids(choix.profil.secteurs)} valeurs={(d.secteurs ?? []).map(String)} placeholder="Chercher un secteur" />
        </Champ>
        <Champ nom="categories" libelle="Catégories" erreurs={erreurs} className="sm:col-span-2">
          <ChoixMultiples id="categories" nom="categories" options={ids(choix.profil.categories)} valeurs={(d.categories ?? []).map(String)} placeholder="Chercher une catégorie" />
        </Champ>
      </Bloc>
      <Bloc titre="Compétences et mots-clés">
        <Champ nom="competences_texte" libelle="Compétences" aide="Séparées par des virgules, 30 au plus." erreurs={erreurs} className="sm:col-span-2">
          <Textarea id="competences_texte" name="competences_texte" defaultValue={d.competences_texte} rows={3} placeholder="SIG, passation de marchés, suivi-évaluation…" />
        </Champ>
        <Champ nom="mots_cles" libelle="Mots-clés" aide="Des mots qui doivent apparaître dans le titre ou la description." erreurs={erreurs} className="sm:col-span-2">
          <Input id="mots_cles" name="mots_cles" defaultValue={d.mots_cles} placeholder="forage, solaire, nutrition" />
        </Champ>
      </Bloc>
      <Enregistrer enCours={enCours} />
    </form>
  )
}

function Preferences({ profil, choix }: { profil: Profil; choix: Reference }) {
  const { surEnvoi, enCours, erreurs } = useSection("preferences")
  const p = profil.preferences
  const [seuil, setSeuil] = useState(p.seuil ?? 40)
  const [teletravail, setTeletravail] = useState(!!p.teletravail)
  const [alertes, setAlertes] = useState(!!p.notifications)
  return (
    <form onSubmit={surEnvoi} className="grid gap-5">
      <Bloc titre="Où" description="Laissez vide pour recevoir des offres de partout.">
        <Champ nom="pays" libelle="Pays" erreurs={erreurs} className="sm:col-span-2">
          <ChoixMultiples id="pref-pays" nom="pays" options={ids(choix.profil.pays)} valeurs={(p.pays ?? []).map(String)} placeholder="Chercher un pays" />
        </Champ>
        <Champ nom="regions" libelle="Régions" erreurs={erreurs} className="sm:col-span-2">
          <Puces nom="regions" etiquette="Régions" options={codes(choix.profil.regions)} valeurs={p.regions ?? []} />
        </Champ>
        <Champ nom="villes" libelle="Villes" aide="Séparées par des virgules." erreurs={erreurs} className="sm:col-span-2">
          <Input id="villes" name="villes" defaultValue={p.villes} placeholder="Antananarivo, Toamasina" />
        </Champ>
      </Bloc>
      <Bloc titre="Quoi">
        <Champ nom="types_offres" libelle="Types d'offres" erreurs={erreurs} className="sm:col-span-2">
          <Puces nom="types_offres" etiquette="Types d'offres" options={codes(choix.profil.types_offres)} valeurs={p.types_offres ?? []} />
        </Champ>
        <div className="flex items-center justify-between gap-4 rounded-xl border p-4 sm:col-span-2">
          <div>
            <Label htmlFor="teletravail">Ouvert au télétravail</Label>
            <p className="text-sm text-muted-foreground">Les offres à distance comptent comme proches de chez vous.</p>
          </div>
          <Switch id="teletravail" checked={teletravail} onCheckedChange={setTeletravail} />
          <input type="hidden" name="teletravail" value={teletravail ? "on" : ""} />
        </div>
      </Bloc>
      <Bloc titre="Suggestions et alertes">
        <div className="grid gap-3 sm:col-span-2">
          <div className="flex items-baseline justify-between">
            <Label htmlFor="seuil">Seuil de pertinence</Label>
            <span className="font-chiffres text-3xl font-light text-marque">{seuil} %</span>
          </div>
          <Slider id="seuil" value={[seuil]} onValueChange={(v) => setSeuil(Array.isArray(v) ? v[0] : v)} min={0} max={100} step={5} />
          <p className="text-sm text-muted-foreground">Seules les offres dont le score atteint ce seuil vous sont proposées.</p>
          <input type="hidden" name="seuil" value={seuil} />
          {erreurs?.seuil && <p className="text-sm text-destructive">{erreurs.seuil.join(" ")}</p>}
        </div>
        <div className="flex items-center justify-between gap-4 rounded-xl border p-4 sm:col-span-2">
          <div>
            <Label htmlFor="notifications">Alertes par email</Label>
            <p className="text-sm text-muted-foreground">Les nouvelles offres qui vous correspondent, après chaque collecte.</p>
          </div>
          <Switch id="notifications" checked={alertes} onCheckedChange={setAlertes} />
          <input type="hidden" name="notifications" value={alertes ? "on" : ""} />
        </div>
      </Bloc>
      <Enregistrer enCours={enCours} />
    </form>
  )
}

function Cv({ profil }: { profil: Profil }) {
  const { surEnvoi, enCours, erreurs } = useFormulaire(deposerCv)
  const [suppression, demarrer] = useTransition()
  const [fichier, setFichier] = useState<string | null>(null)
  const cv = profil.cv
  return (
    <div className="grid gap-5">
      <AnimatePresence initial={false}>
        {cv && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap items-center gap-4 rounded-[22px] verre-carte p-5"
          >
            <span className="grid size-12 place-items-center rounded-xl bg-accent text-accent-foreground">
              <FileTextIcon />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{cv.nom}</p>
              <p className="text-sm text-muted-foreground">Déposé le {date(cv.depose_le)}</p>
            </div>
            <Button variant="outline" nativeButton={false} render={<a href="/bff/profil/cv" download />}>
              <DownloadIcon /> Télécharger
            </Button>
            <Button
              variant="destructive"
              disabled={suppression}
              onClick={() =>
                demarrer(async () => {
                  const r = await supprimerCv()
                  if (r.ok) toast.success(r.message)
                  else toast.error(r.erreur)
                })
              }
            >
              {suppression ? <Spinner /> : <Trash2Icon />} Supprimer
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
      <form onSubmit={surEnvoi} className="grid gap-4 rounded-[22px] border border-dashed border-input bg-card/70 p-8 text-center">
        <UploadIcon className="mx-auto size-8 text-marque" aria-hidden />
        <div>
          <p className="font-medium">{cv ? "Remplacer votre CV" : "Déposer votre CV"}</p>
          <p className="text-sm text-muted-foreground">PDF ou DOCX, 5 Mo au plus. Il reste privé : seuls les administrateurs peuvent le lire.</p>
        </div>
        <Label htmlFor="fichier" className="mx-auto inline-flex cursor-pointer items-center gap-2 rounded-lg border bg-background px-4 py-2 text-sm font-medium hover:bg-muted">
          {fichier ?? "Choisir un fichier"}
        </Label>
        <input
          id="fichier"
          name="fichier"
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          onChange={(e) => setFichier(e.target.files?.[0]?.name ?? null)}
        />
        {erreurs?.fichier && <p className="text-sm text-destructive">{erreurs.fichier.join(" ")}</p>}
        <Button type="submit" disabled={!fichier || enCours} className="mx-auto">
          {enCours && <Spinner />} Déposer le CV
        </Button>
      </form>
    </div>
  )
}

const ONGLETS = [
  { code: "perso", libelle: "Identité" },
  { code: "pro", libelle: "Parcours" },
  { code: "domaines", libelle: "Domaines" },
  { code: "preferences", libelle: "Préférences" },
  { code: "cv", libelle: "CV" },
]

/** Une section par onglet ; l'onglet ouvert est dans l'URL (?onglet=) pour les liens directs. */
export function OngletsProfil({ profil, reference }: { profil: Profil; reference: Reference }) {
  const params = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const initial = ONGLETS.some((o) => o.code === params.get("onglet")) ? params.get("onglet")! : "perso"
  return (
    <Tabs
      defaultValue={initial}
      onValueChange={(v) => router.replace(`${pathname}?onglet=${v}`, { scroll: false })}
      className="mt-8"
    >
      <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <TabsList className="h-11">
          {ONGLETS.map((o) => (
            <TabsTrigger key={o.code} value={o.code} className="px-4">
              {o.libelle}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      <TabsContent value="perso" className="mt-6">
        <Perso profil={profil} choix={reference} />
      </TabsContent>
      <TabsContent value="pro" className="mt-6">
        <Pro profil={profil} choix={reference} />
      </TabsContent>
      <TabsContent value="domaines" className="mt-6">
        <Domaines profil={profil} choix={reference} />
      </TabsContent>
      <TabsContent value="preferences" className="mt-6">
        <Preferences profil={profil} choix={reference} />
      </TabsContent>
      <TabsContent value="cv" className="mt-6">
        <Cv profil={profil} />
      </TabsContent>
    </Tabs>
  )
}
