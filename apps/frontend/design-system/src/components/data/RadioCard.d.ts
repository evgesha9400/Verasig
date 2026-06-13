import { ReactNode, HTMLAttributes } from 'react'

export interface RadioCardProps extends HTMLAttributes<HTMLElement> {
  selected?: boolean
  as?: 'button' | 'a' | 'div'
  href?: string
  children?: ReactNode
}

export function RadioCard(props: RadioCardProps): JSX.Element
