// Langues de l'interface. En ajouter une : son code ici, son nom, puis lib/i18n/<code>.json.
// fr.json et en.json sont complets (verifies par TypeScript) ; les autres peuvent omettre
// des cles, remplacees alors par l'anglais (lib/i18n/index.ts).
export const LANGUES = ["fr", "en", "ar", "it", "es", "de", "pt", "ru", "zh", "ja", "hi", "tr", "nl", "sw"] as const
export type Langue = (typeof LANGUES)[number]
export const LANGUE_DEFAUT: Langue = "fr"
export const COOKIE_LANGUE = "lc_langue"

export const estLangue = (v: unknown): v is Langue => LANGUES.includes(v as Langue)

/** Le nom de chaque langue, ecrit dans cette langue (selecteur de langue). */
export const NOMS: Record<Langue, string> = {
  fr: "Français",
  en: "English",
  ar: "العربية",
  it: "Italiano",
  es: "Español",
  de: "Deutsch",
  pt: "Português",
  ru: "Русский",
  zh: "中文",
  ja: "日本語",
  hi: "हिन्दी",
  tr: "Türkçe",
  nl: "Nederlands",
  sw: "Kiswahili",
}

export const DRAPEAUX: Record<Langue, string> = {
  fr: "🇫🇷", en: "🇬🇧", ar: "🇸🇦", it: "🇮🇹", es: "🇪🇸", de: "🇩🇪", pt: "🇵🇹",
  ru: "🇷🇺", zh: "🇨🇳", ja: "🇯🇵", hi: "🇮🇳", tr: "🇹🇷", nl: "🇳🇱", sw: "🇹🇿",
}

/** Langues ecrites de droite a gauche : la page entiere se retourne. */
export const RTL: readonly Langue[] = ["ar"]
