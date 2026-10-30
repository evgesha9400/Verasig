import { ReactNode, HTMLAttributes } from 'react'

/**
 * Lightweight hover/focus tooltip. Wraps a single trigger child; shows `label`
 * (and an optional `shortcut`) on hover or keyboard focus.
 */
export interface TooltipProps extends HTMLAttributes<HTMLSpanElement> {
  /** Tooltip text. */
  label: string
  /** Which side to show on. @default "top" */
  side?: 'top' | 'bottom'
  /** Optional keyboard shortcut shown in mono. */
  shortcut?: string
  /** The trigger element. */
  children: ReactNode
}

export function Tooltip(props: TooltipProps): JSX.Element
