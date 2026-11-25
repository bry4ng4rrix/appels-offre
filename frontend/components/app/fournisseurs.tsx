"use client"

import { MotionConfig } from "motion/react"
import { ThemeProvider } from "next-themes"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

export function Fournisseurs({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {/* Les animations suivent le reglage « reduire les animations » du systeme. */}
      <MotionConfig reducedMotion="user">
        <TooltipProvider delay={300}>
          {children}
          <Toaster position="bottom-center" />
        </TooltipProvider>
      </MotionConfig>
    </ThemeProvider>
  )
}
