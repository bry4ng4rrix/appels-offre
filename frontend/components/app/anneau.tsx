/** Anneau de progression (completion du profil). */
export function Anneau({ valeur, taille = 64, libelle }: { valeur: number; taille?: number; libelle: string }) {
  const r = 26
  const c = 2 * Math.PI * r
  return (
    <div className="relative grid shrink-0 place-items-center" style={{ width: taille, height: taille }} role="img" aria-label={libelle}>
      <svg viewBox="0 0 64 64" className="absolute inset-0 -rotate-90">
        <defs>
          <linearGradient id="degrade-anneau" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#ebae29" />
            <stop offset="1" stopColor="#589c80" />
          </linearGradient>
        </defs>
        <circle cx="32" cy="32" r={r} fill="none" stroke="var(--muted)" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke="url(#degrade-anneau)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.min(100, valeur) / 100)}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <span className="font-chiffres text-base font-medium">{valeur}%</span>
    </div>
  )
}
