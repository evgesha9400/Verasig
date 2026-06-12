import { ReactNode, HTMLAttributes } from 'react'

export interface PopoverProps extends HTMLAttributes<HTMLSpanElement> {
  trigger: ReactNode
  side?: 'top' | 'bottom'
  align?: 'start' | 'end'
  role?: string
  panelClassName?: string
  children?: ReactNode
}

export function Popover(props: PopoverProps): JSX.Element
