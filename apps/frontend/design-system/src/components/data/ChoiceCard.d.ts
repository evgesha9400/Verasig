import { ReactNode, HTMLAttributes } from 'react'

export interface ChoiceCardProps extends HTMLAttributes<HTMLElement> {
  selected?: boolean
  as?: 'button' | 'a' | 'div'
  href?: string
  children?: ReactNode
}

export function ChoiceCard(props: ChoiceCardProps): JSX.Element
