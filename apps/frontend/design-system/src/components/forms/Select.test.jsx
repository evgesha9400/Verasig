import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Select } from './Select.jsx'

describe('Select', () => {
  it('associates the label with the control via a generated id', () => {
    const { container } = render(
      <Select label="Exchange" options={['Binance', 'Kraken']} />
    )
    const label = container.querySelector('label')
    const select = container.querySelector('select')
    expect(label.getAttribute('for')).toBeTruthy()
    expect(label.getAttribute('for')).toBe(select.getAttribute('id'))
  })

  it('honours an explicitly-passed id', () => {
    const { container } = render(
      <Select id="my-select" label="Exchange" options={['Binance']} />
    )
    expect(container.querySelector('select').getAttribute('id')).toBe('my-select')
    expect(container.querySelector('label').getAttribute('for')).toBe('my-select')
  })

  it('renders children (not an empty option list) when options is an empty array', () => {
    const { container } = render(
      <Select options={[]}>
        <option value="fallback">Fallback</option>
      </Select>
    )
    const options = container.querySelectorAll('option')
    expect(options).toHaveLength(1)
    expect(options[0].value).toBe('fallback')
  })
})
