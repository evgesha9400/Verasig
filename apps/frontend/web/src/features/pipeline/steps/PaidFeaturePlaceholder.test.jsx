import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PaidFeaturePlaceholder } from './PaidFeaturePlaceholder.jsx'

describe('PaidFeaturePlaceholder', () => {
  it('names the deferred feature and invokes onDone', () => {
    const onDone = vi.fn()
    render(<PaidFeaturePlaceholder feature="Exchange routing" onDone={onDone} />)

    expect(screen.getByText(/Exchange routing/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Back to feeds/i }))
    expect(onDone).toHaveBeenCalled()
  })
})
