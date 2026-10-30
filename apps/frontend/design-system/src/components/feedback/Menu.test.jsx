import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Menu, MenuItem } from './Menu.jsx'

function renderMenu() {
  const utils = render(
    <Menu label="Actions">
      <MenuItem>Edit</MenuItem>
      <MenuItem disabled>Locked</MenuItem>
      <MenuItem>Archive</MenuItem>
      <MenuItem>Delete</MenuItem>
    </Menu>
  )
  fireEvent.click(utils.getByRole('button', { name: 'Actions' }))
  return utils
}

describe('Menu keyboard interaction', () => {
  it('moves focus to the first enabled item when it opens', () => {
    const { getByText } = renderMenu()
    expect(document.activeElement).toBe(getByText('Edit').closest('button'))
  })

  it('navigates enabled items with ArrowDown, ArrowUp, Home and End', () => {
    const { getByRole, getByText } = renderMenu()
    const menu = getByRole('menu')
    const item = (label) => getByText(label).closest('button')

    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(document.activeElement).toBe(item('Archive'))
    fireEvent.keyDown(menu, { key: 'End' })
    expect(document.activeElement).toBe(item('Delete'))
    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(document.activeElement).toBe(item('Edit'))
    fireEvent.keyDown(menu, { key: 'ArrowUp' })
    expect(document.activeElement).toBe(item('Delete'))
    fireEvent.keyDown(menu, { key: 'Home' })
    expect(document.activeElement).toBe(item('Edit'))
  })

  it('closes on Escape and returns focus to the trigger', () => {
    const { getByRole, queryByRole } = renderMenu()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(getByRole('button', { name: 'Actions' }))
  })
})
