import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RadioCard } from './RadioCard.jsx'

describe('RadioCard', () => {
  it("keeps its own Enter/Space activation even when the caller passes onKeyDown", () => {
    const onClick = vi.fn()
    const callerKeyDown = vi.fn()
    const { getByRole } = render(
      <RadioCard as="div" onClick={onClick} onKeyDown={callerKeyDown}>
        Option
      </RadioCard>
    )
    fireEvent.keyDown(getByRole('radio'), { key: 'Enter' })
    expect(callerKeyDown).toHaveBeenCalledTimes(1)
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
