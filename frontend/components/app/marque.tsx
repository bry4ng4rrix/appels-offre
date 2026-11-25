import Image from "next/image"

import { cn } from "@/lib/utils"

/** La marque de l'app : « AO » sur fond sombre, avec la pastille rouge du favicon.
 *  Elle s'inverse en theme sombre, comme le favicon. */
export function MarqueAO({ className, pastille = "ring-panneau" }: { className?: string; pastille?: string }) {
  return (
    <span className={cn("relative grid size-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground", className)}>
      <span className="text-[0.95rem] leading-none font-bold tracking-tight">AO</span>
      <span className={cn("absolute top-0.5 right-0.5 size-2.5 rounded-full bg-[#dc2626] ring-2", pastille)} aria-hidden />
    </span>
  )
}

/** Le logo Label Technology, sur fond transparent : seulement dans le pied de page.
 *  Ses lettres blanches deviennent encre en theme clair (logo-label-encre.png). */
export function LogoLabel({ className }: { className?: string }) {
  return (
    <span className={cn("inline-block shrink-0", className)}>
      <Image src="/logo-label-encre.png" alt="Label Technology" width={376} height={256} className="h-12 w-auto dark:hidden" />
      <Image src="/logo-label-blanc.png" alt="Label Technology" width={376} height={256} className="hidden h-12 w-auto dark:block" />
    </span>
  )
}
