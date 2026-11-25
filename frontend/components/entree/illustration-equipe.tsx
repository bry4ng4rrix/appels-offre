/** Deux personnes consultent des offres qui cloturent bientot. Dessin repris de l'app
 *  Django (_illustration_equipe.html), anime en CSS (classes eq-* de globals.css) ;
 *  le decor suit les couleurs du theme. */
export function IllustrationEquipe({ className }: { className?: string }) {
  const decor = "fill-muted-foreground/35"
  return (
    <svg className={className} viewBox="0 0 480 230" role="img" aria-label="Deux personnes consultent des offres qui clôturent bientôt">
      <ellipse cx="240" cy="221" rx="225" ry="6" className="fill-foreground/8" />

      {/* Offres flottantes */}
      <g className="eq-carte" style={{ "--d": "0s" } as React.CSSProperties}>
        <rect x="160" y="10" width="120" height="36" rx="10" className="fill-card stroke-border" />
        <rect x="170" y="19" width="30" height="18" rx="9" fill="#f2bca4" />
        <text x="185" y="32" textAnchor="middle" fontSize="10.5" fontWeight="600" fill="#23241f">J-3</text>
        <rect x="208" y="20" width="60" height="6" rx="3" className="fill-muted-foreground/45" />
        <rect className="eq-ligne fill-muted-foreground/25" x="208" y="30" width="44" height="6" rx="3" />
        <g className="eq-coche">
          <circle cx="279" cy="12" r="9" fill="#589c80" />
          <path d="m274.5 12 3 3 5-6" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      </g>
      <g className="eq-carte" style={{ "--d": "-1.3s" } as React.CSSProperties}>
        <rect x="224" y="52" width="118" height="36" rx="10" className="fill-card stroke-border" />
        <rect x="234" y="61" width="30" height="18" rx="9" fill="#f3d68f" />
        <text x="249" y="74" textAnchor="middle" fontSize="10.5" fontWeight="600" fill="#23241f">J-9</text>
        <rect x="272" y="62" width="58" height="6" rx="3" className="fill-muted-foreground/45" />
        <rect className="eq-ligne fill-muted-foreground/25" style={{ animationDelay: "-.8s" }} x="272" y="72" width="40" height="6" rx="3" />
      </g>
      <g className="eq-carte" style={{ "--d": "-2.6s" } as React.CSSProperties}>
        <rect x="206" y="94" width="118" height="36" rx="10" className="fill-card stroke-border" />
        <rect x="216" y="103" width="36" height="18" rx="9" fill="#bcdccb" />
        <text x="234" y="116" textAnchor="middle" fontSize="10.5" fontWeight="600" fill="#23241f">J-21</text>
        <rect x="260" y="104" width="52" height="6" rx="3" className="fill-muted-foreground/45" />
        <rect className="eq-ligne fill-muted-foreground/25" style={{ animationDelay: "-1.6s" }} x="260" y="114" width="36" height="6" rx="3" />
      </g>

      {/* Bureau, ordinateur, tasse ; plante au sol */}
      <rect x="118" y="150" width="184" height="7" rx="3" className={decor} />
      <rect x="128" y="157" width="6" height="62" className={decor} />
      <rect x="286" y="157" width="6" height="62" className={decor} />
      <rect x="134" y="145" width="52" height="5" rx="2" className="fill-muted-foreground/60" />
      <path d="M184 148 193 110" className="stroke-muted-foreground/70" strokeWidth="5" strokeLinecap="round" />
      <rect x="226" y="139" width="12" height="11" rx="2" className="fill-foreground/70" />
      <path d="M238 142a3.5 3.5 0 0 1 0 6" fill="none" className="stroke-foreground/70" strokeWidth="2" />
      <g transform="translate(58 68)">
        <rect x="256" y="136" width="16" height="14" rx="2" fill="#b45309" />
        <path d="M264 136c-2-8-9-12-14-12 1 6 6 11 14 12Zm0 0c1-9 6-15 12-16 0 7-5 13-12 16Zm0 0c0-8 0-14 1-18" fill="#589c80" stroke="#589c80" strokeWidth="1.5" strokeLinejoin="round" />
      </g>

      {/* Personne assise, a l'ordinateur */}
      <rect x="46" y="118" width="7" height="58" rx="3" className={decor} />
      <rect x="46" y="168" width="56" height="7" rx="3" className={decor} />
      <rect x="72" y="175" width="5" height="40" className={decor} />
      <rect x="56" y="214" width="38" height="5" rx="2.5" className={decor} />
      <rect x="70" y="156" width="62" height="14" rx="7" fill="#64748b" />
      <rect x="120" y="160" width="13" height="56" rx="6" fill="#64748b" />
      <ellipse cx="132" cy="217" rx="11" ry="5" className="fill-foreground/70" />
      <path d="M64 114q16-12 34-2l3 54-35 2Z" fill="var(--ambre)" />
      <rect x="79" y="96" width="9" height="13" rx="3" fill="#f1c27d" />
      <circle cx="86" cy="86" r="14" fill="#f1c27d" />
      <circle cx="94" cy="84" r="1.6" fill="#18181b" />
      <path d="M72 88a14 14 0 0 1 27-8q-9-3-15 3-5 5-12 5Z" fill="#9a3412" />
      <circle cx="71" cy="78" r="7" fill="#9a3412" />
      <g className="eq-tape">
        <path d="M88 118 103 140h36" fill="none" stroke="var(--ambre)" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="143" cy="140" r="5" fill="#f1c27d" />
      </g>

      {/* Personne debout, montre les offres */}
      <rect x="372" y="160" width="13" height="58" rx="6" fill="#57534e" />
      <rect x="388" y="160" width="13" height="58" rx="6" fill="#57534e" />
      <ellipse cx="374" cy="219" rx="11" ry="5" className="fill-foreground/70" />
      <ellipse cx="394" cy="219" rx="11" ry="5" className="fill-foreground/70" />
      <path d="M365 110q20-12 40 0l2 56h-44Z" fill="#34d399" />
      <rect x="380" y="92" width="9" height="13" rx="3" fill="#8d5524" />
      <g className="eq-tete">
        <circle cx="384" cy="82" r="14" fill="#8d5524" />
        <circle cx="377" cy="80" r="1.6" fill="#18181b" />
        <path d="M370 80a14 14 0 0 1 28 0q-6-6-14-5-8 0-14 5Z" fill="#a8a29e" />
      </g>
      <path d="M372 116 359 97l-8-19" fill="none" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="350" cy="74" r="5" fill="#8d5524" />
      <rect x="384" y="128" width="24" height="32" rx="3" fill="#27272a" stroke="#71717a" />
      <rect x="388" y="132" width="16" height="22" rx="1.5" fill="var(--ambre)" opacity=".55" />
      <path d="M402 116 410 138l-14 8" fill="none" stroke="#34d399" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="396" cy="146" r="5" fill="#8d5524" />
    </svg>
  )
}
