import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Loader } from './Loader.jsx'

describe('Loader', () => {
  it('renders the bar glyph by default', () => {
    const { container } = render(<Loader />)
    expect(container.querySelector('.vrs-loader-bar')).toBeTruthy()
    expect(container.querySelector('.vrs-loader-dot')).toBeNull()
  })

  it('renders the dot glyph on variant="dot"', () => {
    const { container } = render(<Loader variant="dot" />)
    expect(container.querySelector('.vrs-loader-dot')).toBeTruthy()
    expect(container.querySelector('.vrs-loader-bar')).toBeNull()
  })

  it('announces politely via role=status', () => {
    const { getByRole } = render(<Loader title="Loading" />)
    expect(getByRole('status').getAttribute('aria-live')).toBe('polite')
  })

  it('renders title and note in the centered block', () => {
    const { getByText } = render(
      <Loader title="Loading signals" note="Almost there." />
    )
    expect(getByText('Loading signals')).toBeTruthy()
    expect(getByText('Almost there.')).toBeTruthy()
  })

  it('renders a bare glyph (no block) when given neither title nor note', () => {
    const { container } = render(<Loader />)
    expect(container.querySelector('.vrs-loader')).toBeNull()
    expect(container.firstChild).toHaveProperty('tagName', 'SPAN')
  })

  it('scales the glyph with size', () => {
    const { container } = render(<Loader variant="dot" size="lg" />)
    expect(container.querySelector('.vrs-loader-dot--lg')).toBeTruthy()
  })
})
