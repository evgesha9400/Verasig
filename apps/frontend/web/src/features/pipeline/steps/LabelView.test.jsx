import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MESSAGES } from '../../../domain/demo-data/seed.js'
import { LabelView } from './LabelView.jsx'

describe('LabelView', () => {
  it('keeps swipe action callbacks wired through DS icon buttons', () => {
    const onLabel = vi.fn()

    render(
      <LabelView
        messages={MESSAGES.slice(0, 2)}
        labels={{}}
        onLabel={onLabel}
        signalCount={0}
        noiseCount={0}
        onDistill={() => {}}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Signal' }))

    expect(onLabel).toHaveBeenCalledWith(MESSAGES[0].id, 'signal')
  })
})
