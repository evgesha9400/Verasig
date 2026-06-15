import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MessageCard } from './MessageCard.jsx'

describe('MessageCard', () => {
  it('renders the message text and the head slot', () => {
    const { container } = render(
      <MessageCard text="LONG BTC" head={<span>HEAD</span>} />
    )
    expect(screen.getByText('LONG BTC')).toBeTruthy()
    expect(screen.getByText('HEAD')).toBeTruthy()
    expect(container.querySelector('.vrs-card-msg')).toBeTruthy()
  })

  it('maps tone to the signal / noise modifier class', () => {
    const signal = render(<MessageCard text="a" tone="signal" />)
    expect(signal.container.querySelector('.vrs-card-msg.is-signal')).toBeTruthy()
    const noise = render(<MessageCard text="b" tone="noise" />)
    expect(noise.container.querySelector('.vrs-card-msg.is-noise')).toBeTruthy()
    const none = render(<MessageCard text="c" />)
    expect(none.container.querySelector('.is-signal, .is-noise')).toBeNull()
  })

  it('renders the reply context when replyTo is given', () => {
    render(
      <MessageCard text="update" replyTo={{ author: 'Apex', text: 'LONG BTC' }} />
    )
    expect(screen.getByText('Apex')).toBeTruthy()
    expect(screen.getByText('LONG BTC')).toBeTruthy()
  })

  it('renders a media label when media is given', () => {
    render(<MessageCard text="x" media="chart" />)
    expect(screen.getByText('Chart screenshot')).toBeTruthy()
  })

  it('shows the drag stamps with custom labels only on the top card', () => {
    const top = render(
      <MessageCard text="x" isTop stampPositive="Correct" stampNegative="Wrong" />
    )
    expect(top.container.querySelector('.vrs-card-stamp.signal').textContent).toBe(
      'Correct'
    )
    expect(top.container.querySelector('.vrs-card-stamp.noise').textContent).toBe(
      'Wrong'
    )

    const buried = render(
      <MessageCard text="x" stampPositive="Correct" stampNegative="Wrong" />
    )
    expect(buried.container.querySelector('.vrs-card-stamp')).toBeNull()
  })

  it('applies the drag transform on the top card', () => {
    const { container } = render(<MessageCard text="x" isTop dragX={44} />)
    const card = container.querySelector('.vrs-card-msg')
    expect(card.style.transform).toContain('translateX(44px)')
  })
})
