import type { Metadata, Viewport } from "next"
import { Noto_Sans, Noto_Sans_Arabic, Noto_Sans_Devanagari, Poppins } from "next/font/google"
import { notFound } from "next/navigation"

import { Fournisseurs } from "@/components/app/fournisseurs"
import { DICOS } from "@/lib/i18n"
import { LANGUES, RTL, estLangue } from "@/lib/i18n/langues"
import "../globals.css"

const poppins = Poppins({
  subsets: ["latin", "latin-ext"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
})
// Ecritures que Poppins ne couvre pas. preload: false : telechargees seulement si la page
// contient de l'arabe, du devanagari ou du cyrillique (le chinois et le japonais : polices du systeme).
const arabe = Noto_Sans_Arabic({ subsets: ["arabic"], weight: ["300", "400", "500", "600"], variable: "--font-arabe", preload: false })
const devanagari = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["300", "400", "500", "600"], variable: "--font-devanagari", preload: false })
const cyrillique = Noto_Sans({ subsets: ["cyrillic"], weight: ["300", "400", "500", "600"], variable: "--font-cyrillique", preload: false })

/** Une version de chaque page par langue (proxy.ts choisit laquelle servir). */
export function generateStaticParams() {
  return LANGUES.map((lang) => ({ lang }))
}

export async function generateMetadata({ params }: LayoutProps<"/[lang]">): Promise<Metadata> {
  const { lang } = await params
  const d = DICOS[estLangue(lang) ? lang : "fr"]
  return {
    metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
    title: { default: d.titres.site, template: "%s · Label Collectes" },
    description: d.titres.description,
    icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }], apple: "/apple-touch-icon.png" },
    openGraph: { images: "/og.png", locale: d.locale.split("-u-")[0].replace("-", "_"), siteName: "Label Collectes" },
  }
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#589c80" },
    { media: "(prefers-color-scheme: dark)", color: "#0d2321" },
  ],
}

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params
  if (!estLangue(lang)) notFound()
  return (
    <html
      lang={lang}
      dir={RTL.includes(lang) ? "rtl" : "ltr"}
      suppressHydrationWarning
      className={`${poppins.variable} ${arabe.variable} ${devanagari.variable} ${cyrillique.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <Fournisseurs langue={lang}>{children}</Fournisseurs>
      </body>
    </html>
  )
}
