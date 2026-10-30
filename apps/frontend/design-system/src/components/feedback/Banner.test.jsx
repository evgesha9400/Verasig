import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Banner } from './Banner.jsx'

const roleOf = (ui) => render(ui).container.firstChild.getAttribute('role')

describe('Banner ARIA live semantics', () => {
  it('announces the error (rejected) tone assertively with role=alert', () => {
    expect(roleOf(<Banner tone="rejected">Failed</Banner>)).toBe('alert')
  })

  it('keeps non-error tones as role=status', () => {
    expect(roleOf(<Banner tone="info">Info</Banner>)).toBe('status')
    expect(roleOf(<Banner tone="verified">Done</Banner>)).toBe('status')
  })
})
