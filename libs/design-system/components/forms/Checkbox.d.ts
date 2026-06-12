import { InputHTMLAttributes } from 'react'

/**
 * Checkbox with an optional label and description line. Native checkbox under
 * the hood — works controlled or uncontrolled.
 */
export interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Label text beside the box. */
  label?: string
  /** Secondary description under the label. */
  description?: string
}

export function Checkbox(props: CheckboxProps): JSX.Element
