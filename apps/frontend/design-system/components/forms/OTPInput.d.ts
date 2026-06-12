import { HTMLAttributes } from 'react'

export interface OTPInputProps extends HTMLAttributes<HTMLDivElement> {
  length?: number
  value?: string
  onChange?: (value: string) => void
  disabled?: boolean
  inputMode?: 'numeric' | 'decimal' | 'tel' | 'text'
}

export function OTPInput(props: OTPInputProps): JSX.Element
