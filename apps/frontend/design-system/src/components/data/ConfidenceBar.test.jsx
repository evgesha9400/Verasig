import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ConfidenceBar } from './ConfidenceBar.jsx'

function fillColor(container) {
  return container.querySelector('.vrs-conf__fill').style.background
}

describe('ConfidenceBar colorFor', () => {
  it('reaches the verified color for a top score even with a high threshold', () => {
    // threshold + 8 = 103 > 100; without clamping, a perfect score stayed pending.
    const { container } = render(<ConfidenceBar value={100} threshold={95} />)
    expect(fillColor(container)).toBe('var(--verified-500)')
  })

  it('is rejected below the threshold', () => {
    const { container } = render(<ConfidenceBar value={70} threshold={80} />)
    expect(fillColor(container)).toBe('var(--rejected-500)')
  })
})
