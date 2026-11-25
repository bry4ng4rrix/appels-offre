import type { Metadata, Viewport } from "next"
import { Poppins } from "next/font/google"

import { Fournisseurs } from "@/components/app/fournisseurs"
import "./globals.css"

const poppins = Poppins({
  subsets: ["latin", "latin-ext"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
})

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: { default: "Label Collectes, appels d'offres à saisir", template: "%s · Label Collectes" },
  description:
    "Les appels d'offres et offres d'emploi des bailleurs, des Nations unies, des ONG et des marchés publics, triés par secteur, pays et date limite.",
  icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }], apple: "/apple-touch-icon.png" },
  openGraph: { images: "/og.png", locale: "fr_FR", siteName: "Label Collectes" },
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#e6e9df" },
    { media: "(prefers-color-scheme: dark)", color: "#121410" },
  ],
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" suppressHydrationWarning className={`${poppins.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Fournisseurs>{children}</Fournisseurs>
      </body>
    </html>
  )
}
