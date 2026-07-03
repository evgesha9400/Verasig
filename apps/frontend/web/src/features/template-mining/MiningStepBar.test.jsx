import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MiningStepBar } from './MiningStepBar.jsx'

function step(label) {
  return screen.getByText(label).closest('.vrs-tm-step')
}

describe('MiningStepBar', () => {
  it('marks the active step and the steps before it as done', () => {
    render(<MiningStepBar active="review" canVerify={false} onNavigate={() => {}} />)
    expect(step('Mine').classList.contains('is-done')).toBe(true)
    expect(step('Review').classList.contains('is-active')).toBe(true)
    expect(step('Verify').classList.contains('is-done')).toBe(false)
    expect(step('Verify').classList.contains('is-active')).toBe(false)
  })

  it('lets you go back from Verify to Review', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<MiningStepBar active="verify" canVerify onNavigate={onNavigate} />)
    await user.click(screen.getByText('Review'))
    expect(onNavigate).toHaveBeenCalledWith('review')
  })

  it('lets you go forward to Verify from Review once it is reachable', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<MiningStepBar active="review" canVerify onNavigate={onNavigate} />)
    await user.click(screen.getByText('Verify'))
    expect(onNavigate).toHaveBeenCalledWith('verify')
  })

  it('does not reach Verify from Review while it is not reachable', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<MiningStepBar active="review" canVerify={false} onNavigate={onNavigate} />)
    await user.click(screen.getByText('Verify'))
    expect(onNavigate).not.toHaveBeenCalled()
  })

  it('never navigates to Mine (a process step)', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<MiningStepBar active="verify" canVerify onNavigate={onNavigate} />)
    await user.click(screen.getByText('Mine'))
    expect(onNavigate).not.toHaveBeenCalledWith('mine')
  })
})
