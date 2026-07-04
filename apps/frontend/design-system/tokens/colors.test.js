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
