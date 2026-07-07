import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Tabs } from './Tabs.jsx'

describe('Tabs', () => {
  it('renders tab triggers with type="button" so they never submit a form', () => {
    const { getAllByRole } = render(<Tabs items={['One', 'Two']} value="One" />)
    for (const tab of getAllByRole('tab')) {
      expect(tab.getAttribute('type')).toBe('button')
    }
  })
})
