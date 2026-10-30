import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const src = dirname(fileURLToPath(import.meta.url))

function read(path) {
  return readFileSync(join(src, path), 'utf8')
}

function filesUnder(path) {
  const root = join(src, path)
  return readdirSync(root).flatMap((entry) => {
    const fullPath = join(root, entry)
    const relativePath = join(path, entry)
    return statSync(fullPath).isDirectory() ? filesUnder(relativePath) : [relativePath]
  })
}

describe('frontend design-system guards', () => {
  it('keeps DS input focus policy out of page-level CSS', () => {
    const pageCss = [
      read('features/auth/auth.css'),
      read('features/marketing/marketing.css'),
      read('app/app.css')
    ].join('\n')

    expect(pageCss).not.toMatch(/\.vrs-input\s+input:focus-visible/)
    expect(pageCss).not.toMatch(/\.vrs-input\s+input:focus,/)
  })

  it('does not keep local duplicate behavioural selectors', () => {
    const pageCss = [
      read('features/marketing/marketing.css'),
      read('app/app.css')
    ].join('\n')

    expect(pageCss).not.toContain('.mk-theme__btn')
    expect(pageCss).not.toContain('.vrs-um__seg-btn')
    expect(pageCss).not.toContain('.vrs-menu button')
    expect(pageCss).not.toContain('.vrs-swipe-btn')
    expect(pageCss).not.toContain('.vrs-next-card')
  })

  it('keeps old top-level ownership folders removed', () => {
    expect(existsSync(join(src, 'auth'))).toBe(false)
    expect(existsSync(join(src, 'marketing'))).toBe(false)
    expect(existsSync(join(src, 'product'))).toBe(false)
    expect(existsSync(join(src, 'routes'))).toBe(false)
  })

  it('keeps domain free of app and UI dependencies', () => {
    const domainFiles = filesUnder('domain').filter((path) => /\.(js|jsx)$/.test(path))
    const domainSource = domainFiles.map(read).join('\n')

    expect(domainSource).not.toMatch(/from ['"]react['"]/)
    expect(domainSource).not.toContain('react-router-dom')
    expect(domainSource).not.toContain('@verasig/design-system')
    expect(domainSource).not.toMatch(/import ['"].+\\.css['"]/)
  })

  it('keeps backfill scanned-progress status readable', () => {
    const appCss = read('app/app.css')
    const match = appCss.match(/\.vrs-bf-log\s*\{(?<body>[^}]*)\}/)

    expect(match?.groups?.body).toContain('font-size: var(--text-sm)')
    expect(match?.groups?.body).toContain('color: var(--text-strong)')
    expect(match?.groups?.body).toContain('line-height:')
    expect(match?.groups?.body).toContain('min-height:')
  })

  it('keeps features from importing app modules', () => {
    const featureFiles = filesUnder('features').filter((path) =>
      /\.(js|jsx)$/.test(path)
    )
    const featureSource = featureFiles.map(read).join('\n')

    expect(featureSource).not.toMatch(/from ['"].*\/app\//)
  })
})
