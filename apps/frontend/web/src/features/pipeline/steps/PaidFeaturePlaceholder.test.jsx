import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PaidFeaturePlaceholder } from './PaidFeaturePlaceholder.jsx'

describe('PaidFeaturePlaceholder', () => {
  it('names the deferred feature and invokes onDone', () => {
    const onDone = vi.fn()
    render(<PaidFeaturePlaceholder feature="Exchange routing" onDone={onDone} />)

    expect(screen.getByText('Exchange routing is a Trader feature')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Back to feeds/i }))
    expect(onDone).toHaveBeenCalled()
  })

  it('names the plan that unlocks a locked feature', () => {
    render(
      <PaidFeaturePlaceholder feature="Execution" planName="Desk" onDone={vi.fn()} />
    )

    expect(screen.getByText('Execution is a Desk feature')).toBeTruthy()
    expect(screen.getByText(/available on the Desk plan/)).toBeTruthy()
  })
})
