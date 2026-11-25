import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"

/** Un champ de formulaire avec son libelle, son aide et ses erreurs (renvoyees par l'API). */
export function Champ({
  nom,
  libelle,
  aide,
  erreurs,
  children,
  className,
}: {
  nom: string
  libelle: React.ReactNode
  aide?: React.ReactNode
  erreurs?: Record<string, string[]>
  children: React.ReactNode
  className?: string
}) {
  const liste = erreurs?.[nom]
  return (
    <Field data-invalid={!!liste || undefined} className={className}>
      <FieldLabel htmlFor={nom}>{libelle}</FieldLabel>
      {children}
      {aide && !liste && <FieldDescription>{aide}</FieldDescription>}
      {liste && <FieldError>{liste.join(" ")}</FieldError>}
    </Field>
  )
}
