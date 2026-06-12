import { ReactNode, HTMLAttributes } from 'react'

/**
 * Compact status badge — mono, uppercase, pill-shaped. Use for verification
 * states and short statuses. For interactive removable chips use `Tag`.
 */
export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** Semantic color. @default "neutral" */
  tone?: 'neutral' | 'verified' | 'pending' | 'rejected' | 'info' | 'outline' | 'solid'
  /** Show a leading status dot. @default false */
  dot?: boolean
  children?: ReactNode
}

export function Badge(props: BadgeProps): JSX.Element
