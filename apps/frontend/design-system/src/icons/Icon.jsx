/* Verasig prototype — inline line icons (house style: 1.8px stroke, round caps) */
// Static glyph map — hoisted to module scope so it is built once, not per render.
const P = {
  sources: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  signals: (
    <>
      <path d="M3 12h3l2 6 4-14 3 10 2-4h4" />
    </>
  ),
  exchanges: (
    <>
      <path d="M3 7h13l-3-3M21 17H8l3 3" />
    </>
  ),
  settings: (
    <>
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  plus: (
    <>
      <path d="M12 5v14M5 12h14" />
    </>
  ),
  check: (
    <>
      <path d="M20 6 9 17l-5-5" />
    </>
  ),
  x: (
    <>
      <path d="M18 6 6 18M6 6l12 12" />
    </>
  ),
  arrowRight: (
    <>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </>
  ),
  arrowLeft: (
    <>
      <path d="M19 12H5M11 18l-6-6 6-6" />
    </>
  ),
  arrowUp: (
    <>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </>
  ),
  arrowDown: (
    <>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </>
  ),
  chevronRight: (
    <>
      <path d="m9 6 6 6-6 6" />
    </>
  ),
  chevronLeft: (
    <>
      <path d="m15 6-6 6 6 6" />
    </>
  ),
  refresh: (
    <>
      <path d="M21 12a9 9 0 1 1-2.6-6.3M21 3v6h-6" />
    </>
  ),
  play: (
    <>
      <path d="M7 4.5 19 12 7 19.5z" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
    </>
  ),
  chart: (
    <>
      <path d="M4 19V5M4 19h16M8 16l3-5 3 3 4-7" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="1.6" />
      <path d="m5 18 5-5 4 4 2-2 3 3" />
    </>
  ),
  doc: (
    <>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0M17 8a3 3 0 0 1 0 6M21 20a5 5 0 0 0-4-4.9" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="14" r="4" />
      <path d="m11 11 8-8 2 2-2 2 1.5 1.5M16 6l1.5 1.5" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 4 6v6c0 4.5 3.2 7.5 8 9 4.8-1.5 8-4.5 8-9V6z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  sparkles: (
    <>
      <path d="M12 3l1.8 4.8L18.5 9.5 13.8 11.3 12 16l-1.8-4.7L5.5 9.5l4.7-1.7z" />
      <path d="M18 15l.7 1.8 1.8.7-1.8.7L18 20l-.7-1.8L15.5 17.5l1.8-.7z" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </>
  ),
  telegram: (
    <>
      <path d="M21.5 4.3 2.9 11.4c-.9.4-.9 1.6 0 1.9l4.6 1.4 1.8 5.6c.3.8 1.3 1 1.9.4l2.5-2.4 4.6 3.4c.7.5 1.6.1 1.8-.7l3.3-15.4c.2-1-.7-1.8-1.6-1.4z" />
    </>
  ),
  discord: (
    <>
      <path d="M8 5.5c-2 .4-4 1.2-4 1.2C2 11 2 16 2 16s2 1.6 5 2l1-1.5c-1.5-.4-2.4-1-2.4-1M16 5.5c2 .4 4 1.2 4 1.2 2 4.3 2 9.3 2 9.3s-2 1.6-5 2l-1-1.5c1.5-.4 2.4-1 2.4-1M9 12.5h.01M15 12.5h.01M8.5 5.2 9 4s2-.4 3-.4 3 .4 3 .4l.5 1.2" />
    </>
  ),
  lock: (
    <>
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M6 7l1 13h10l1-13" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  logout: (
    <>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 17l5-5-5-5M15 12H3" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: (
    <>
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </>
  ),
  unfold: (
    <>
      <path d="m7 15 5 5 5-5M7 9l5-5 5 5" />
    </>
  ),
  alert: (
    <>
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </>
  ),
  externalLink: (
    <>
      <path d="M14 4h6v6" />
      <path d="M20 4 11 13" />
      <path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5" />
    </>
  ),
  spark: (
    <>
      <path d="M4 14h6l-2 6 8-12h-6l2-6z" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.8" fill="currentColor" />
    </>
  ),
  reply: (
    <>
      <path d="M9 16 4 11l5-5" />
      <path d="M4 11h11a5 5 0 0 1 5 5v3" />
    </>
  ),
  link: (
    <>
      <path d="M10 13.5a4.5 4.5 0 0 0 6.8.5l2.7-2.7a4.5 4.5 0 0 0-6.4-6.4l-1.5 1.5" />
      <path d="M14 10.5a4.5 4.5 0 0 0-6.8-.5l-2.7 2.7a4.5 4.5 0 0 0 6.4 6.4l1.5-1.5" />
    </>
  ),
  layers: (
    <>
      <path d="m12 3 9 5-9 5-9-5z" />
      <path d="m3 13 9 5 9-5" />
    </>
  ),
  binance: (
    <g fill="currentColor" stroke="none">
      <path d="M12 2.4 15.2 5.6 12 8.8 8.8 5.6Z" />
      <path d="M5.6 8.8 8.8 12 5.6 15.2 2.4 12Z" />
      <path d="M18.4 8.8 21.6 12 18.4 15.2 15.2 12Z" />
      <path d="M12 8.8 15.2 12 12 15.2 8.8 12Z" />
      <path d="M12 15.2 15.2 18.4 12 21.6 8.8 18.4Z" />
    </g>
  ),
  bybit: (
    <g fill="currentColor" stroke="none" fillRule="evenodd">
      <path d="M6 3h2.7v7.1a5.3 5.3 0 0 1 3.4-1.2 5.55 5.55 0 1 1 0 11.1 5.3 5.3 0 0 1-3.5-1.3V21H6V3Zm6 8.5a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" />
    </g>
  )
}

export function Icon({ name, size = 18, fill = false, style }) {
  const glyph = P[name]
  if (!glyph && import.meta.env?.DEV) {
    console.warn(`[Icon] unknown icon name: "${name}"`)
  }
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={fill ? 'currentColor' : 'none'}
      stroke={fill ? 'none' : 'currentColor'}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
    >
      {glyph}
    </svg>
  )
}
