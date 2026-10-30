import { ReactNode, ButtonHTMLAttributes } from 'react'

/**
 * Square, icon-only button for toolbars and dense controls. Always pass `label`
 * for accessibility (used as aria-label + tooltip title).
 */
export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style. @default "ghost" */
  variant?: 'ghost' | 'solid' | 'accent'
  /** @default "md" */
  size?: 'sm' | 'md' | 'lg'
  /** Accessible label + tooltip text. Required. */
  label: string
  /** Icon node (e.g. an SVG). */
  children?: ReactNode
}

export function IconButton(props: IconButtonProps): JSX.Element
