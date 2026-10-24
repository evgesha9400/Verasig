import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button.jsx'
import { IconButton } from './IconButton.jsx'

const here = dirname(fileURLToPath(import.meta.url))
const baseCss = readFileSync(join(here, '../../../tokens/base.css'), 'utf8')

// Every `selector { body }` rule in a flat stylesheet (no nested blocks).
function cssRules(css) {
  const rules = []
  const pattern = /([^{}]+)\{([^}]*)\}/g
  let match
  while ((match = pattern.exec(css.replace(/\/\*[\s\S]*?\*\//g, ''))) !== null) {
    rules.push({ selector: match[1].trim(), body: match[2] })
  }
  return rules
}

function ruleBody(css, selector) {
  const rule = cssRules(css).find((r) => r.selector === selector)
  expect(rule, selector).toBeDefined()
  return rule.body
}

function buttonCss() {
  return document.getElementById('vrs-button-css').textContent
}

describe('Button as an anchor', () => {
  it('blocks clicks and marks itself disabled when as="a" and disabled', () => {
    const onClick = vi.fn()
    const { getByText } = render(
      <Button as="a" href="#next" disabled onClick={onClick}>
        Next
      </Button>
    )
    const link = getByText('Next')
    expect(link.getAttribute('aria-disabled')).toBe('true')
    fireEvent.click(link)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('still fires clicks when the anchor is enabled', () => {
    const onClick = vi.fn()
    const { getByText } = render(
      <Button as="a" href="#next" onClick={onClick}>
        Go
      </Button>
    )
    fireEvent.click(getByText('Go'))
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(getByText('Go').getAttribute('aria-disabled')).toBeNull()
  })
})

// jsdom cannot force :hover, so these lock the cascade contract instead:
// the base anchor colors carry zero specificity and only reach class-less
// links, and every variant re-asserts its own text color while hovered or
// pressed. Together they keep <Button as="a"> / <Button as={Link}> from
// turning link-blue on hover.
describe('Button as an anchor keeps its variant color on hover', () => {
  it('scopes the base link colors to class-less anchors at zero specificity', () => {
    const anchorColorRules = cssRules(baseCss).filter(
      (r) => /(^|[\s,(])a\b/.test(r.selector) && /(^|[\s;])color\s*:/.test(r.body)
    )
    expect(anchorColorRules.map((r) => r.selector)).toEqual([
      ':where(a:not([class]))',
      ':where(a:not([class]):hover)'
    ])
    expect(anchorColorRules[0].body).toMatch(/color:\s*var\(--link\)/)
    expect(anchorColorRules[1].body).toMatch(/color:\s*var\(--link-hover\)/)
  })

  it.each([
    ['primary', 'var(--text-on-accent)'],
    ['secondary', 'var(--text-strong)'],
    ['danger', 'var(--rejected-500)']
  ])('%s re-asserts %s on :hover and :active', (variant, color) => {
    render(
      <Button as="a" href="#go" variant={variant}>
        Go
      </Button>
    )
    for (const state of ['hover', 'active']) {
      const body = ruleBody(buttonCss(), `.vrs-btn__${variant}:${state}:not(:disabled)`)
      expect(body).toMatch(
        new RegExp(`(^|[\\s;])color: ${color.replace(/[()]/g, '\\$&')}`)
      )
    }
  })
})

// jsdom cannot force :focus-visible + :hover either, so prove from the CSS that
// whenever any variant/theme/state rule sets box-shadow, a focus-ring rule
// still applies under the same conditions and wins the cascade.
const STATE_TOKENS = [':hover', ':active', ':not(:disabled)', "[data-theme='light']"]

function specificity(selector) {
  return (selector.replace(/:not\(/g, '(').match(/\.[\w-]+|\[[^\]]+\]|:[\w-]+/g) || [])
    .length
}

function conditions(selector) {
  return STATE_TOKENS.filter((token) => selector.includes(token))
}

function focusRingCoverage(css, root) {
  const entries = cssRules(css).flatMap((rule, index) =>
    rule.selector.split(',').map((selector) => ({
      selector: selector.trim(),
      body: rule.body,
      index
    }))
  )
  const rings = entries.filter(
    (e) =>
      e.selector.includes(`.${root}:focus-visible`) &&
      /var\(--focus-ring\)/.test(e.body)
  )
  const shadows = entries.filter(
    (e) =>
      /box-shadow\s*:/.test(e.body) &&
      !e.selector.includes(':focus-visible') &&
      !/:disabled\b(?!\))/.test(e.selector.replace(/:not\(:disabled\)/g, ''))
  )
  expect(rings.length).toBeGreaterThan(0)
  expect(shadows.length).toBeGreaterThan(0)
  return shadows
    .filter(
      (shadow) =>
        !rings.some(
          (ring) =>
            conditions(ring.selector).every((c) => shadow.selector.includes(c)) &&
            (specificity(ring.selector) > specificity(shadow.selector) ||
              (specificity(ring.selector) === specificity(shadow.selector) &&
                ring.index > shadow.index))
        )
    )
    .map((shadow) => shadow.selector)
}

describe('focus ring survives every variant, theme and pointer state', () => {
  it('Button: no box-shadow rule can override the :focus-visible ring', () => {
    render(<Button variant="secondary">Go</Button>)
    expect(focusRingCoverage(buttonCss(), 'vrs-btn')).toEqual([])
  })

  it('Button: light secondary and :hover box-shadows are explicitly covered', () => {
    const rings = cssRules(buttonCss())
      .filter((r) => /var\(--focus-ring\)/.test(r.body))
      .flatMap((r) => r.selector.split(',').map((x) => x.trim()))
    expect(rings).toContain('.vrs-btn:focus-visible')
    expect(rings).toContain('.vrs-btn:focus-visible:hover:not(:disabled)')
    expect(rings).toContain(
      "[data-theme='light'] .vrs-btn:focus-visible:hover:not(:disabled)"
    )
  })

  it('IconButton: no box-shadow rule can override the :focus-visible ring', () => {
    render(<IconButton label="Close" variant="solid" />)
    const css = document.getElementById('vrs-iconbtn-css').textContent
    expect(focusRingCoverage(css, 'vrs-iconbtn')).toEqual([])
  })
})

describe('light pressed keys drop the hover gradient', () => {
  it.each([
    [
      'vrs-button-css',
      "[data-theme='light'] .vrs-btn__secondary:active:not(:disabled)"
    ],
    [
      'vrs-iconbtn-css',
      "[data-theme='light'] .vrs-iconbtn__solid:active:not(:disabled)"
    ]
  ])('%s %s clears background-image', (id, selector) => {
    render(
      <>
        <Button variant="secondary">Go</Button>
        <IconButton label="Close" variant="solid" />
      </>
    )
    expect(ruleBody(document.getElementById(id).textContent, selector)).toMatch(
      /background-image:\s*none/
    )
  })
})
