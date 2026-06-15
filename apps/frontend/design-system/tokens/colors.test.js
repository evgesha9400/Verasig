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
