"use client"

import { MotionConfig } from "motion/react"
import { ThemeProvider } from "next-themes"

import { Traductions } from "@/components/app/traductions"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import type { Langue } from "@/lib/i18n/langues"

export function Fournisseurs({ langue, children }: { langue: Langue; children: React.ReactNode }) {
  return (
    <Traductions langue={langue}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {/* Les animations suivent le reglage « reduire les animations » du systeme. */}
      <MotionConfig reducedMotion="user">
        <TooltipProvider delay={300}>
          {children}
          <Toaster position="bottom-center" mobileOffset={{ bottom: 88 }} />
        </TooltipProvider>
      </MotionConfig>
    </ThemeProvider>
    </Traductions>
  )
}
