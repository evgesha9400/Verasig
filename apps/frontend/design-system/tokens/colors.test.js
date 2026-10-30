import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const colorsCss = readFileSync(join(here, 'colors.css'), 'utf8')
const themeProvider = readFileSync(
  join(here, '../src/components/theme/ThemeProvider.jsx'),
  'utf8'
)

function lightBlock() {
  const start = colorsCss.indexOf("[data-theme='light']")
  expect(start).toBeGreaterThan(-1)
  return colorsCss.slice(start)
}

describe('colors.css light theme signal ramp', () => {
  // The JS ThemeProvider inline-overrides --signal-400/500/600 to azure in light.
  // The CSS [data-theme='light'] block MUST carry the same ramp so the cascade
  // source is complete and never falls through to the :root lime values.
  it('repoints the full signal ramp to the azure ramp under [data-theme="light"]', () => {
    const light = lightBlock()
    expect(light).toMatch(/--signal-300:\s*var\(--azure-300\)/)
    expect(light).toMatch(/--signal-400:\s*var\(--azure-400\)/)
    expect(light).toMatch(/--signal-500:\s*var\(--azure-500\)/)
    expect(light).toMatch(/--signal-600:\s*var\(--azure-600\)/)
    expect(light).toMatch(/--signal-700:\s*var\(--azure-700\)/)
  })

  it('defines the azure ramp shades the light signal ramp depends on', () => {
    expect(colorsCss).toMatch(/--azure-300:\s*#[0-9a-fA-F]{6}/)
    expect(colorsCss).toMatch(/--azure-700:\s*#[0-9a-fA-F]{6}/)
  })

  // Guards the JS<->CSS agreement the audit flagged: the azure shades the light
  // signal ramp maps to must equal the literal hexes ThemeProvider sets inline.
  it('keeps the azure shades equal to the ThemeProvider light inline values', () => {
    expect(colorsCss).toMatch(/--azure-400:\s*#82b6ff/i)
    expect(colorsCss).toMatch(/--azure-500:\s*#5197ff/i)
    expect(colorsCss).toMatch(/--azure-600:\s*#2f6fe0/i)
    expect(themeProvider).toMatch(/hover:\s*'#82B6FF'/)
    expect(themeProvider).toMatch(/accent:\s*'#5197FF'/)
    expect(themeProvider).toMatch(/press:\s*'#2F6FE0'/)
  })
})

// ============================================================
// WCAG AA text-contrast guard.
// Faint/muted labels were unreadable on Sources/Exchanges/Signals.
// Lock the fix at the token layer: every text token must clear the
// 4.5:1 AA floor for normal text against every opaque surface, in
// BOTH themes — so no label can silently regress into illegibility.
// ============================================================

const AA_NORMAL = 4.5

const TEXT_TOKENS = [
  '--text-strong',
  '--text-heading',
  '--text-body',
  '--text-muted',
  '--text-faint'
]

const OPAQUE_SURFACES = [
  '--bg-void',
  '--bg-app',
  '--surface-sunken',
  '--surface-card',
  '--surface-raised',
  '--surface-hover',
  '--surface-overlay'
]

function rootBlock() {
  const opener = colorsCss.match(/:root\s*\{/)
  const lightStart = colorsCss.indexOf("[data-theme='light']")
  expect(opener).not.toBeNull()
  expect(lightStart).toBeGreaterThan(opener.index)
  return colorsCss.slice(opener.index, lightStart)
}

function parseDeclarations(block) {
  const declarations = {}
  const pattern = /(--[\w-]+)\s*:\s*([^;]+);/g
  let match
  while ((match = pattern.exec(block)) !== null) {
    declarations[match[1]] = match[2].trim()
  }
  return declarations
}

// Dark lives on :root; light overrides layer on top of it (light omits the
// raw palette, so it must fall back to the :root ink/azure ramps).
const DARK_TOKENS = parseDeclarations(rootBlock())
const LIGHT_TOKENS = { ...DARK_TOKENS, ...parseDeclarations(lightBlock()) }
const THEME_TOKENS = { dark: DARK_TOKENS, light: LIGHT_TOKENS }

function resolveHex(name, tokens, depth = 0) {
  if (depth > 10) throw new Error(`var() chain too deep resolving ${name}`)
  const value = tokens[name]
  if (value === undefined) throw new Error(`token ${name} is not defined`)
  const reference = value.match(/var\(\s*(--[\w-]+)\s*\)/)
  if (reference) return resolveHex(reference[1], tokens, depth + 1)
  if (!/^#[0-9a-fA-F]{6}$/.test(value)) {
    throw new Error(`token ${name} did not resolve to a 6-digit hex (got: ${value})`)
  }
  return value
}

function channelToLinear(channel) {
  const c = channel / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

function relativeLuminance(hex) {
  const [r, g, b] = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16))
    .map(channelToLinear)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrastRatio(foreground, background) {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background))
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background))
  return (lighter + 0.05) / (darker + 0.05)
}

describe('colors.css text tokens meet WCAG AA on every surface', () => {
  for (const theme of Object.keys(THEME_TOKENS)) {
    const tokens = THEME_TOKENS[theme]
    for (const textToken of TEXT_TOKENS) {
      it(`${theme}: ${textToken} clears 4.5:1 on all opaque surfaces`, () => {
        const foreground = resolveHex(textToken, tokens)
        const failures = []
        for (const surfaceToken of OPAQUE_SURFACES) {
          const background = resolveHex(surfaceToken, tokens)
          const ratio = contrastRatio(foreground, background)
          if (ratio < AA_NORMAL) {
            failures.push(`${surfaceToken} (${background}) → ${ratio.toFixed(2)}:1`)
          }
        }
        expect(failures).toEqual([])
      })
    }
  }
})

// ============================================================
// Light-theme semantic separation + surface elevation guards.
// Verified (green) and info (blue) must never collapse into one hue,
// and the light surfaces must stay distinct so hover/raised states
// remain visible on white.
// ============================================================

const SEMANTIC_TEXT_TOKENS = ['--verified-500', '--info-500']
const ELEVATION_SURFACES = [
  '--surface-sunken',
  '--surface-card',
  '--surface-raised',
  '--surface-hover'
]

describe('colors.css semantic hues stay distinct', () => {
  for (const theme of Object.keys(THEME_TOKENS)) {
    const tokens = THEME_TOKENS[theme]

    it(`${theme}: --verified-500 and --info-500 are different colors`, () => {
      const verified = resolveHex('--verified-500', tokens).toLowerCase()
      const info = resolveHex('--info-500', tokens).toLowerCase()
      expect(verified).not.toBe(info)
    })

    it(`${theme}: verified/info text clears 4.5:1 on --surface-card`, () => {
      const card = resolveHex('--surface-card', tokens)
      for (const token of SEMANTIC_TEXT_TOKENS) {
        const ratio = contrastRatio(resolveHex(token, tokens), card)
        expect(ratio, `${token} on --surface-card`).toBeGreaterThanOrEqual(AA_NORMAL)
      }
    })

    it(`${theme}: elevation surfaces are all distinct`, () => {
      const hexes = ELEVATION_SURFACES.map((token) =>
        resolveHex(token, tokens).toLowerCase()
      )
      expect(new Set(hexes).size).toBe(hexes.length)
    })
  }

  it('light: verified is emerald and info is the deep azure', () => {
    expect(resolveHex('--verified-500', LIGHT_TOKENS).toLowerCase()).toBe('#0f6a30')
    expect(resolveHex('--info-500', LIGHT_TOKENS).toLowerCase()).toBe('#1d56c9')
    expect(LIGHT_TOKENS['--verified-bg']).toBe('rgba(15, 106, 48, 0.1)')
    expect(LIGHT_TOKENS['--info-bg']).toBe('rgba(29, 86, 201, 0.1)')
  })
})

// ============================================================
// Semantic text sits on its own tinted --*-bg (Badge, StatusPill,
// danger hover). Alpha-composite each tint over the opaque light
// surfaces it renders on and require AA for the matching foreground.
// ============================================================

function parseRgba(value) {
  const match = value.match(
    /^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)$/
  )
  if (!match) throw new Error(`not an rgba() literal: ${value}`)
  return { rgb: match.slice(1, 4).map(Number), alpha: Number(match[4]) }
}

function composite(rgbaValue, backgroundHex) {
  const { rgb, alpha } = parseRgba(rgbaValue)
  return (
    '#' +
    rgb
      .map((channel, i) => {
        const base = parseInt(backgroundHex.slice(1 + i * 2, 3 + i * 2), 16)
        return Math.round(channel * alpha + base * (1 - alpha))
      })
      .map((channel) => channel.toString(16).padStart(2, '0'))
      .join('')
  )
}

describe('light semantic text clears AA on its own tinted background', () => {
  for (const hue of ['verified', 'info', 'pending', 'rejected']) {
    for (const surface of ['--surface-card', '--surface-sunken']) {
      it(`--${hue}-500 on --${hue}-bg over ${surface}`, () => {
        const background = composite(
          LIGHT_TOKENS[`--${hue}-bg`],
          resolveHex(surface, LIGHT_TOKENS)
        )
        const ratio = contrastRatio(
          resolveHex(`--${hue}-500`, LIGHT_TOKENS),
          background
        )
        expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL)
      })
    }
  }
})

// ============================================================
// Light accent text (selected segments, accent icon buttons, tabs)
// must clear AA on every opaque surface, and the light focus ring
// must clear the 3:1 non-text floor on every opaque surface.
// ============================================================

describe('light accent text and focus ring contrast', () => {
  it('--accent-text clears 4.5:1 on all opaque surfaces', () => {
    const foreground = resolveHex('--accent-text', LIGHT_TOKENS)
    for (const surface of OPAQUE_SURFACES) {
      const ratio = contrastRatio(foreground, resolveHex(surface, LIGHT_TOKENS))
      expect(ratio, surface).toBeGreaterThanOrEqual(AA_NORMAL)
    }
  })

  it('--border-focus clears 3:1 on all opaque surfaces', () => {
    const ring = resolveHex('--border-focus', LIGHT_TOKENS)
    for (const surface of OPAQUE_SURFACES) {
      const ratio = contrastRatio(ring, resolveHex(surface, LIGHT_TOKENS))
      expect(ratio, surface).toBeGreaterThanOrEqual(3)
    }
  })

  it('keeps ThemeProvider light accent text equal to --azure-700', () => {
    expect(colorsCss).toMatch(/--azure-700:\s*#1d56c9/i)
    expect(themeProvider).toMatch(/text:\s*'#1D56C9'/)
    expect(themeProvider).toMatch(/verified:\s*'#0F6A30'/)
  })
})

// ============================================================
// --text-on-accent must stay legible on the primary button at rest
// and while pressed (the :active fill is a black color-mix of the
// accent, read from Button.jsx so the test tracks the real CSS).
// ============================================================

const buttonSource = readFileSync(
  join(here, '../src/components/core/Button.jsx'),
  'utf8'
)

function primaryPressMix() {
  const match = buttonSource.match(
    /\.vrs-btn__primary:active:not\(:disabled\)\s*\{[^}]*color-mix\(in srgb, var\(--accent\) (\d+)%, #000\)/
  )
  expect(match).not.toBeNull()
  return Number(match[1]) / 100
}

function mixWithBlack(hex, weight) {
  return (
    '#' +
    [1, 3, 5]
      .map((i) => Math.round(parseInt(hex.slice(i, i + 2), 16) * weight))
      .map((channel) => channel.toString(16).padStart(2, '0'))
      .join('')
  )
}

describe('--text-on-accent clears AA on the primary button', () => {
  for (const theme of Object.keys(THEME_TOKENS)) {
    const tokens = THEME_TOKENS[theme]

    it(`${theme}: on --accent at rest`, () => {
      const ratio = contrastRatio(
        resolveHex('--text-on-accent', tokens),
        resolveHex('--accent', tokens)
      )
      expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL)
    })

    it(`${theme}: on the pressed (:active) fill`, () => {
      const pressed = mixWithBlack(resolveHex('--accent', tokens), primaryPressMix())
      const ratio = contrastRatio(resolveHex('--text-on-accent', tokens), pressed)
      expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL)
    })
  }
})

// ============================================================
// Light theme replaces the deep black dark-UI shadows with soft,
// ink-tinted ones so cards and popovers do not look smudged on white.
// ============================================================

describe('effects.css light shadows', () => {
  const effectsCss = readFileSync(join(here, 'effects.css'), 'utf8')

  it('overrides every elevation shadow with a soft ink tint under [data-theme="light"]', () => {
    const start = effectsCss.indexOf("[data-theme='light']")
    expect(start).toBeGreaterThan(-1)
    const light = parseDeclarations(effectsCss.slice(start))
    for (const token of [
      '--shadow-xs',
      '--shadow-sm',
      '--shadow-md',
      '--shadow-lg',
      '--shadow-pop'
    ]) {
      expect(light[token], token).toMatch(/rgba\(12, 18, 26, 0\.(0[5-9]|1[0-4])\)/)
    }
  })
})
