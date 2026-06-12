import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const src = dirname(fileURLToPath(import.meta.url))

function read(path) {
  return readFileSync(join(src, path), 'utf8')
}

describe('frontend design-system guards', () => {
  it('keeps DS input focus policy out of page-level CSS', () => {
    const pageCss = [
      read('auth/auth.css'),
      read('marketing/marketing.css'),
      read('product/product.css')
    ].join('\n')

    expect(pageCss).not.toMatch(/\.vrs-input\s+input:focus-visible/)
    expect(pageCss).not.toMatch(/\.vrs-input\s+input:focus,/)
  })

  it('does not keep local duplicate behavioural selectors', () => {
    const pageCss = [read('marketing/marketing.css'), read('product/product.css')].join(
      '\n'
    )

    expect(pageCss).not.toContain('.mk-theme__btn')
    expect(pageCss).not.toContain('.vrs-um__seg-btn')
    expect(pageCss).not.toContain('.vrs-menu button')
    expect(pageCss).not.toContain('.vrs-swipe-btn')
    expect(pageCss).not.toContain('.vrs-next-card')
  })
})
