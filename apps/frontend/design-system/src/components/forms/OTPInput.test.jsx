import { useState } from 'react'
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OTPInput } from './OTPInput.jsx'

function Controlled({ inputMode, length = 5 }) {
  const [value, setValue] = useState('')
  return (
    <OTPInput length={length} value={value} onChange={setValue} inputMode={inputMode} />
  )
}

describe('OTPInput per-cell integrity', () => {
  it('keeps each digit in its own cell, preserving an empty middle cell', () => {
    const { container } = render(<Controlled />)
    const inputs = [...container.querySelectorAll('input')]

    fireEvent.change(inputs[0], { target: { value: '1' } })
    fireEvent.change(inputs[2], { target: { value: '3' } })

    expect(inputs[0].value).toBe('1')
    expect(inputs[1].value).toBe('')
    expect(inputs[2].value).toBe('3')
  })
})

describe('OTPInput inputMode', () => {
  it('restricts to digits when inputMode is numeric', () => {
    const { container } = render(<Controlled inputMode="numeric" />)
    const inputs = [...container.querySelectorAll('input')]
    fireEvent.change(inputs[0], { target: { value: 'a' } })
    expect(inputs[0].value).toBe('')
  })

  it('accepts non-numeric characters when inputMode is not numeric', () => {
    const { container } = render(<Controlled inputMode="text" />)
    const inputs = [...container.querySelectorAll('input')]
    fireEvent.change(inputs[0], { target: { value: 'a' } })
    expect(inputs[0].value).toBe('a')
  })
})
