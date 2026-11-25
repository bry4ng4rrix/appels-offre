import Image from "next/image"

import { cn } from "@/lib/utils"

/** Le logo Label Technology (blanc et bleu) sur un disque sombre, dans les deux themes. */
export function Tuile({ className }: { className?: string }) {
  return (
    <span className={cn("grid size-9 shrink-0 place-items-center rounded-lg bg-[#1d201b] ring-1 ring-black/5", className)}>
      <Image src="/logo-label.png" alt="" width={512} height={341} className="w-[78%] -translate-y-[5%]" priority />
    </span>
  )
}
