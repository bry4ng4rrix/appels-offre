"use client"

import { BellIcon, ChevronDownIcon, CreditCardIcon, KeyRoundIcon, LogOutIcon, UserRoundIcon } from "lucide-react"
import Link from "next/link"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { deconnexion } from "@/lib/actions/compte"

type Props = { email: string; nom: string; admin: boolean; photo: boolean }

export function MenuCompte({ email, nom, admin, photo }: Props) {
  const initiale = (nom || email).charAt(0).toUpperCase()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            className="verre-carte h-10 gap-2 rounded-full pr-3 pl-1"
            aria-label={`Mon compte : ${email}`}
          />
        }
      >
        <Avatar className="size-8">
          {photo && <AvatarImage src="/bff/profil/photo" alt="" className="object-cover" />}
          <AvatarFallback className="bg-ambre text-xs font-semibold text-ambre-foreground">{initiale}</AvatarFallback>
        </Avatar>
        <span className="hidden max-w-36 truncate text-sm font-normal lg:inline">{nom || email}</span>
        <ChevronDownIcon className="size-4 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="truncate">
            {nom && <span className="block text-sm font-medium text-foreground">{nom}</span>}
            <span className="block truncate text-xs text-muted-foreground">
              {email}
              {admin && ", administrateur"}
            </span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem render={<Link href="/profil" />}>
            <UserRoundIcon /> Mon profil
          </DropdownMenuItem>
          <DropdownMenuItem render={<Link href="/notifications" />}>
            <BellIcon /> Mes notifications
          </DropdownMenuItem>
          {!admin && (
            <DropdownMenuItem render={<Link href="/abonnement" />}>
              <CreditCardIcon /> Abonnement
            </DropdownMenuItem>
          )}
          <DropdownMenuItem render={<Link href="/compte/mot-de-passe" />}>
            <KeyRoundIcon /> Changer le mot de passe
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => deconnexion()}>
          <LogOutIcon /> Se déconnecter
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
