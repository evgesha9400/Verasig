import { ReactNode, InputHTMLAttributes } from 'react'

/**
 * Text input with label, hint, error and optional leading icon / trailing node.
 * Set `mono` for IDs, keys, and endpoints.
 */
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Field label rendered above the control. */
  label?: string
  /** Helper text below the field. */
  hint?: string
  /** Error message — also flips the field to the error style. */
  error?: string
  /** Show a required asterisk. @default false */
  required?: boolean
  /** Leading icon node. */
  iconLeft?: ReactNode
  /** Trailing node (kbd hint, unit, button). */
  trailing?: ReactNode
  /** Use the mono font (signal IDs, keys, endpoints). @default false */
  mono?: boolean
}

export function Input(props: InputProps): JSX.Element
