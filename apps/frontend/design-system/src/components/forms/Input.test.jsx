import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Input } from './Input.jsx'

describe('Input', () => {
  it('uses an explicitly-passed id for both the label and the control', () => {
    const { container } = render(<Input id="email" label="Email" />)
    const label = container.querySelector('label')
    const input = container.querySelector('input')
    expect(input.getAttribute('id')).toBe('email')
    expect(label.getAttribute('for')).toBe('email')
  })

  it('generates distinct ids for two inputs that share a label', () => {
    const { container } = render(
      <div>
        <Input label="Amount" />
        <Input label="Amount" />
      </div>
    )
    const inputs = container.querySelectorAll('input')
    expect(inputs[0].getAttribute('id')).toBeTruthy()
    expect(inputs[0].getAttribute('id')).not.toBe(inputs[1].getAttribute('id'))
  })

  it('marks an errored input invalid and describes it by the error message', () => {
    const { container, getByText } = render(
      <Input label="Email" error="Enter a valid email" aria-describedby="extra" />
    )
    const input = container.querySelector('input')
    const message = getByText('Enter a valid email')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(message.id).toBeTruthy()
    expect(input.getAttribute('aria-describedby')).toBe(`extra ${message.id}`)
  })

  it('describes a valid input by its hint without marking it invalid', () => {
    const { container, getByText } = render(<Input label="Email" hint="Work email" />)
    const input = container.querySelector('input')
    expect(input.hasAttribute('aria-invalid')).toBe(false)
    expect(input.getAttribute('aria-describedby')).toBe(getByText('Work email').id)
  })
})
