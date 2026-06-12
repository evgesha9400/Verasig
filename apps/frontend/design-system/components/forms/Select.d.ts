import { ReactNode, SelectHTMLAttributes } from 'react'

export interface SelectOption {
  value: string
  label: string
}

/**
 * Styled native `<select>`. Provide `options` (strings or `{value,label}`) or
 * raw `<option>` children.
 */
export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  /** Field label. */
  label?: string
  /** Option list — strings or `{value, label}`. */
  options?: (SelectOption | string)[]
  children?: ReactNode
}

export function Select(props: SelectProps): JSX.Element
