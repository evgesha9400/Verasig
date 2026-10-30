import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const colorsCss = readFileSync(join(here, 'colors.css'), 'utf8')
// ============================================================
// WCAG AA text-contrast guard.
// Faint/muted labels were unreadable on Sources/Exchanges/Signals.
// Lock the fix at the token layer: every text token must clear the
// 4.5:1 AA floor for normal text against every opaque surface, so no
// label can silently regress into illegibility.
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
  expect(opener).not.toBeNull()
  return colorsCss.slice(opener.index)
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

const TOKENS = parseDeclarations(rootBlock())

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
  for (const textToken of TEXT_TOKENS) {
    it(`${textToken} clears 4.5:1 on all opaque surfaces`, () => {
      const foreground = resolveHex(textToken, TOKENS)
      const failures = []
      for (const surfaceToken of OPAQUE_SURFACES) {
        const background = resolveHex(surfaceToken, TOKENS)
        const ratio = contrastRatio(foreground, background)
        if (ratio < AA_NORMAL) {
          failures.push(`${surfaceToken} (${background}) → ${ratio.toFixed(2)}:1`)
        }
      }
      expect(failures).toEqual([])
    })
  }
})

// ============================================================
// Semantic separation + surface elevation guards.
// Verified and info must never collapse into one hue, and the
// surfaces must stay distinct so hover/raised states remain visible.
// ============================================================

const SEMANTIC_TEXT_TOKENS = ['--verified-500', '--info-500']
const ELEVATION_SURFACES = [
  '--surface-sunken',
  '--surface-card',
  '--surface-raised',
  '--surface-hover'
]

describe('colors.css semantic hues stay distinct', () => {
  it('--verified-500 and --info-500 are different colors', () => {
    const verified = resolveHex('--verified-500', TOKENS).toLowerCase()
    const info = resolveHex('--info-500', TOKENS).toLowerCase()
    expect(verified).not.toBe(info)
  })

  it('verified/info text clears 4.5:1 on --surface-card', () => {
    const card = resolveHex('--surface-card', TOKENS)
    for (const token of SEMANTIC_TEXT_TOKENS) {
      const ratio = contrastRatio(resolveHex(token, TOKENS), card)
      expect(ratio, `${token} on --surface-card`).toBeGreaterThanOrEqual(AA_NORMAL)
    }
  })

  it('elevation surfaces are all distinct', () => {
    const hexes = ELEVATION_SURFACES.map((token) =>
      resolveHex(token, TOKENS).toLowerCase()
    )
    expect(new Set(hexes).size).toBe(hexes.length)
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
  it('on --accent at rest', () => {
    const ratio = contrastRatio(
      resolveHex('--text-on-accent', TOKENS),
      resolveHex('--accent', TOKENS)
    )
    expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('on the pressed (:active) fill', () => {
    const pressed = mixWithBlack(resolveHex('--accent', TOKENS), primaryPressMix())
    const ratio = contrastRatio(resolveHex('--text-on-accent', TOKENS), pressed)
    expect(ratio).toBeGreaterThanOrEqual(AA_NORMAL)
  })
})
