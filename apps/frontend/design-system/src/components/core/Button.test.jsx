import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button.jsx'

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
