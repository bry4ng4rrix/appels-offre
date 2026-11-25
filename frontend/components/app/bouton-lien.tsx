import Link from "next/link"
import type { ComponentProps } from "react"

import { Button } from "@/components/ui/button"

type Props = Omit<ComponentProps<typeof Button>, "render" | "nativeButton"> & {
  href: string
  prefetch?: boolean
  externe?: boolean
}

/** Un lien qui a l'allure d'un bouton. */
export function BoutonLien({ href, prefetch, externe, ...props }: Props) {
  const lien = externe ? <a href={href} target="_blank" rel="noopener noreferrer" /> : <Link href={href} prefetch={prefetch} />
  return <Button nativeButton={false} render={lien} {...props} />
}
