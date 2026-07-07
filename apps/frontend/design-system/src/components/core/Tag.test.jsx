import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Tag } from './Tag.jsx'

describe('Tag', () => {
  it('gives the remove button type="button" so it never submits a form', () => {
    const { getByLabelText } = render(<Tag onRemove={() => {}}>BTC</Tag>)
    expect(getByLabelText('Remove').getAttribute('type')).toBe('button')
  })

  it('exposes an interactive tag as a keyboard-operable button', () => {
    const onClick = vi.fn()
    const { getByText } = render(<Tag onClick={onClick}>BTC</Tag>)
    const tag = getByText('BTC')
    expect(tag.getAttribute('role')).toBe('button')
    expect(tag.getAttribute('tabindex')).toBe('0')
    fireEvent.keyDown(tag, { key: 'Enter' })
    fireEvent.keyDown(tag, { key: ' ' })
    expect(onClick).toHaveBeenCalledTimes(2)
  })

  it('stays a plain span with no keyboard affordance when not interactive', () => {
    const { getByText } = render(<Tag>BTC</Tag>)
    const tag = getByText('BTC')
    expect(tag.getAttribute('role')).toBeNull()
    expect(tag.getAttribute('tabindex')).toBeNull()
  })
})
