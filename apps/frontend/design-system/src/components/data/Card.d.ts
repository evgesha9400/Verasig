import { ReactNode, HTMLAttributes } from 'react'

/**
 * Surface container — the base card used across the app. Optional header
 * (title/subtitle/actions) and footer. Use `interactive` for clickable cards
 * and `glow` to highlight a live/active state.
 */
export interface CardProps extends HTMLAttributes<HTMLElement> {
  /** Header title. */
  title?: string
  /** Header subtitle. */
  subtitle?: string
  /** Right-aligned header actions (buttons, badges). */
  headerActions?: ReactNode
  /** Footer node. */
  footer?: ReactNode
  /** Apply default body padding. @default true */
  padded?: boolean
  /** Visual state. @default "static" */
  variant?: 'static' | 'interactive' | 'selected' | 'overlay'
  /** Rendered element. @default "div" */
  as?: 'div' | 'button' | 'a'
  /** Button type when `as="button"`. @default "button" */
  type?: 'button' | 'submit' | 'reset'
  /** Link target when `as="a"`. */
  href?: string
  /** Disabled state when `as="button"`. */
  disabled?: boolean
  /** Selected state. @default false */
  selected?: boolean
  /** Hover lift + pointer cursor. Legacy alias for variant="interactive". @default false */
  interactive?: boolean
  /** Signal glow border (live/active). @default false */
  glow?: boolean
  children?: ReactNode
}

export function Card(props: CardProps): JSX.Element
