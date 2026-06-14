import { fireEvent, render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import * as DS from './index.js'
import { Icon } from './src/icons/Icon.jsx'

describe('design-system barrel', () => {
  const expected = [
    'Avatar',
    'Badge',
    'Button',
    'IconButton',
    'TextLink',
    'Tabs',
    'Tag',
    'Card',
    'ConfidenceBar',
    'MetricStat',
    'SignalRow',
    'StatusPill',
    'Banner',
    'Dialog',
    'Toast',
    'ToastStack',
    'Tooltip',
    'ThemeProvider',
    'ThemeToggle',
    'useTheme',
    'SegmentedControl',
    'InteractiveCard',
    'ChoiceCard',
    'RadioCard',
    'Menu',
    'MenuItem',
    'Popover',
    'OTPInput',
    'Checkbox',
    'Input',
    'Select',
    'Switch',
    'Icon'
  ]
  it.each(expected)('exports %s', (name) => {
    expect(typeof DS[name]).toBe('function')
  })
})

describe('design-system interaction contracts', () => {
  it('uses the same focus token for Button and IconButton', () => {
    render(
      <>
        <DS.Button>Save</DS.Button>
        <DS.IconButton label="Refresh">
          <Icon name="refresh" />
        </DS.IconButton>
      </>
    )

    expect(document.getElementById('vrs-button-css').textContent).toContain(
      'var(--focus-ring)'
    )
    expect(document.getElementById('vrs-iconbtn-css').textContent).toContain(
      'var(--focus-ring)'
    )
  })

  it('keeps pressed buttons stationary so pointer-up still registers clicks', () => {
    render(
      <>
        <DS.Button>Back</DS.Button>
        <DS.IconButton label="Refresh">
          <Icon name="refresh" />
        </DS.IconButton>
      </>
    )

    expect(document.getElementById('vrs-button-css').textContent).not.toContain(
      'transform: translateY(1px)'
    )
    expect(document.getElementById('vrs-iconbtn-css').textContent).not.toContain(
      'transform: translateY(1px)'
    )
  })

  it('TextLink renders <a> with href and <button> as a real action', () => {
    const onClick = vi.fn()
    render(
      <>
        <DS.TextLink href="https://example.com">Docs</DS.TextLink>
        <DS.TextLink onClick={onClick}>Resend</DS.TextLink>
      </>
    )

    expect(screen.getByRole('link', { name: 'Docs' }).getAttribute('href')).toBe(
      'https://example.com'
    )

    const button = screen.getByRole('button', { name: 'Resend' })
    expect(button.getAttribute('type')).toBe('button')
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('ThemeToggle renders radio options and calls onChange', () => {
    const onChange = vi.fn()
    render(<DS.ThemeToggle value="dark" onChange={onChange} />)

    expect(screen.getByRole('radiogroup', { name: 'Theme' })).toBeTruthy()
    expect(
      screen.getByRole('radio', { name: 'Dark' }).getAttribute('aria-checked')
    ).toBe('true')

    fireEvent.click(screen.getByRole('radio', { name: 'Light' }))
    expect(onChange).toHaveBeenCalledWith('light')
  })

  it('SegmentedControl exposes radiogroup and radio semantics', () => {
    const onChange = vi.fn()
    render(
      <DS.SegmentedControl
        label="Density"
        value="regular"
        onChange={onChange}
        options={[
          { value: 'compact', label: 'Compact' },
          { value: 'regular', label: 'Regular' }
        ]}
      />
    )

    expect(screen.getByRole('radiogroup', { name: 'Density' })).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Compact' }))
    expect(onChange).toHaveBeenCalledWith('compact')
  })

  it('InteractiveCard renders a real button for clickable cards', () => {
    const onClick = vi.fn()
    render(<DS.InteractiveCard onClick={onClick}>Open source</DS.InteractiveCard>)

    fireEvent.click(screen.getByRole('button', { name: 'Open source' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('ChoiceCard and RadioCard expose selection through ARIA', () => {
    render(
      <>
        <DS.ChoiceCard selected>Choice</DS.ChoiceCard>
        <DS.RadioCard selected>Radio</DS.RadioCard>
      </>
    )

    expect(
      screen.getByRole('button', { name: 'Choice' }).getAttribute('aria-pressed')
    ).toBe('true')
    expect(
      screen.getByRole('radio', { name: 'Radio' }).getAttribute('aria-checked')
    ).toBe('true')
  })

  it('Menu and MenuItem expose menu roles', () => {
    render(
      <DS.Menu trigger={<DS.IconButton label="Options">⋯</DS.IconButton>}>
        <DS.MenuItem>Refresh</DS.MenuItem>
      </DS.Menu>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Options' }))
    expect(screen.getByRole('menu')).toBeTruthy()
    expect(screen.getByRole('menuitem', { name: 'Refresh' })).toBeTruthy()
  })

  it('Popover opens on focus-compatible trigger semantics', () => {
    render(
      <DS.Popover trigger={<span>Details</span>}>
        <span>Rich content</span>
      </DS.Popover>
    )

    const trigger = screen.getByText('Details').closest('.vrs-pop__trigger')
    expect(trigger.getAttribute('tabindex')).toBe('0')
    expect(screen.getByRole('tooltip').textContent).toContain('Rich content')
  })

  it('OTPInput moves digit state through onChange', () => {
    const onChange = vi.fn()
    render(<DS.OTPInput length={5} value="" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Digit 1'), { target: { value: '7' } })
    expect(onChange).toHaveBeenCalledWith('7')
  })

  it('OTPInput pastes a code using the configured length', () => {
    const onChange = vi.fn()
    render(<DS.OTPInput length={6} value="" onChange={onChange} />)

    fireEvent.paste(screen.getByLabelText('Digit 1'), {
      clipboardData: { getData: () => '123456' }
    })

    expect(onChange).toHaveBeenLastCalledWith('123456')
  })
})
