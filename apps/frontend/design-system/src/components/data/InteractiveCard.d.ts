import { ReactNode, HTMLAttributes } from 'react'

export interface InteractiveCardProps extends HTMLAttributes<HTMLElement> {
  as?: 'button' | 'a' | 'div'
  href?: string
  selected?: boolean
  children?: ReactNode
}

export function InteractiveCard(props: InteractiveCardProps): JSX.Element
