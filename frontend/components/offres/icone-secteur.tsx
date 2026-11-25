import {
  BriefcaseBusinessIcon,
  CpuIcon,
  DropletsIcon,
  GraduationCapIcon,
  HardHatIcon,
  HeartPulseIcon,
  LandmarkIcon,
  LeafIcon,
  MegaphoneIcon,
  ScaleIcon,
  SproutIcon,
  TruckIcon,
  UtensilsIcon,
  UsersIcon,
  ZapIcon,
  type LucideIcon,
} from "lucide-react"

// Les codes de secteur sont libres (fusions, langues) : on reconnait un mot-cle.
const ICONES: [RegExp, LucideIcon][] = [
  [/sant|sanit|medic/, HeartPulseIcon],
  [/informat|numer|electron|techno/, CpuIcon],
  [/constru|archit|travaux|btp/, HardHatIcon],
  [/eau|assain/, DropletsIcon],
  [/energ|electri/, ZapIcon],
  [/agri|elevage/, SproutIcon],
  [/educ|format/, GraduationCapIcon],
  [/financ|assur|banc/, LandmarkIcon],
  [/transport|logist/, TruckIcon],
  [/environ|climat/, LeafIcon],
  [/gouvern|admin|public|recht/, ScaleIcon],
  [/communic|media/, MegaphoneIcon],
  [/alimen|nutri/, UtensilsIcon],
  [/social|humanit/, UsersIcon],
]

export function IconeSecteur({ code, className }: { code?: string | null; className?: string }) {
  const Icone = ICONES.find(([motif]) => motif.test(code ?? ""))?.[1] ?? BriefcaseBusinessIcon
  return <Icone className={className} aria-hidden />
}
