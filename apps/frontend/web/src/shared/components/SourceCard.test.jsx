import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SourceCard } from './SourceCard.jsx'

describe('SourceCard', () => {
  it('renders the title block, description and foot slots', () => {
    const { container } = render(
      <SourceCard
        logo={<span data-testid="logo" />}
        name="Telegram"
        kind="Signal source"
        badge={<span>Connected</span>}
        desc="some description"
        meta={<span>meta</span>}
        action={<button type="button">Connect</button>}
      />
    )
    expect(screen.getByText('Telegram')).toBeTruthy()
    expect(screen.getByText('Signal source')).toBeTruthy()
    expect(screen.getByText('some description')).toBeTruthy()
    expect(screen.getByTestId('logo')).toBeTruthy()
    expect(screen.getByText('Connected')).toBeTruthy()
    expect(container.querySelector('.vrs-src-card__top')).toBeTruthy()
    expect(container.querySelector('.vrs-src-card__foot')).toBeTruthy()
  })

  it('renders an empty variant with only the description', () => {
    const { container } = render(<SourceCard empty desc="No sources yet." />)
    expect(container.querySelector('.vrs-src-card--empty')).toBeTruthy()
    expect(container.querySelector('.vrs-src-card__top')).toBeNull()
    expect(screen.getByText('No sources yet.')).toBeTruthy()
  })

  it('renders a clickable button card when onClick is given', () => {
    const onClick = vi.fn()
    render(<SourceCard name="Telegram" kind="src" onClick={onClick} />)
    const card = screen.getByRole('button', { name: /telegram/i })
    fireEvent.click(card)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('lets children replace the default desc/foot body', () => {
    const { container } = render(
      <SourceCard name="Bybit" kind="exchange">
        <div className="custom-body">config form</div>
      </SourceCard>
    )
    expect(screen.getByText('config form')).toBeTruthy()
    expect(container.querySelector('.vrs-src-card__foot')).toBeNull()
    expect(container.querySelector('.vrs-src-card__top')).toBeTruthy()
  })
})
