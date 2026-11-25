/** Le panneau clair ou vivent les contenus (comme les cartes de la maquette). */
export function Panneau({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`verre rounded-[30px] p-5 sm:p-8 ${className}`}>{children}</section>
}
