import { InputHTMLAttributes } from 'react'

/**
 * Toggle switch for binary on/off settings (e.g. enable a channel). For
 * multi-select use Checkbox.
 */
export interface SwitchProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Label rendered to the right of the switch. */
  label?: string
}

export function Switch(props: SwitchProps): JSX.Element
