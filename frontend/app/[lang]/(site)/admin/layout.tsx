import { Suspense } from "react"

import { exigerAdmin } from "@/lib/session"

/** Tout /admin/ est reserve aux admins (404 sinon) ; l'API reverifie chaque appel. */
export default function LayoutAdmin({ children }: LayoutProps<"/admin">) {
  return (
    <Suspense fallback={null}>
      <Garde>{children}</Garde>
    </Suspense>
  )
}

async function Garde({ children }: { children: React.ReactNode }) {
  await exigerAdmin()
  return children
}
