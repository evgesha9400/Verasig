import { ReactNode, HTMLAttributes } from 'react'

export interface SegmentedControlOption {
  value?: string
  id?: string
  label: string
  ariaLabel?: string
  title?: string
  icon?: ReactNode
  disabled?: boolean
}

export interface SegmentedControlProps extends HTMLAttributes<HTMLDivElement> {
  value: string
  onChange?: (value: string) => void
  options: SegmentedControlOption[]
  label?: string
  size?: 'sm' | 'md'
  iconOnly?: boolean
}

export function SegmentedControl(props: SegmentedControlProps): JSX.Element
