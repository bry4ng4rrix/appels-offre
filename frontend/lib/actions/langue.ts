"use server"

import { refresh } from "next/cache"
import { cookies } from "next/headers"

import { COOKIE_LANGUE, estLangue } from "@/lib/i18n/langues"

/** Retient la langue choisie ; le proxy sert ensuite chaque page dans cette langue. */
export async function changerLangue(langue: string) {
  if (!estLangue(langue)) return
  ;(await cookies()).set(COOKIE_LANGUE, langue, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" })
  refresh()
}
