import { ReactNode } from 'react'

export interface SplitButtonOption {
  /** Stable value passed to onSelect. */
  value: string
  /** Menu row label. */
  label: string
}

/**
 * A default action fused with a dropdown of alternatives (e.g. a "Start
 * backfill" button whose caret opens a menu of history depths). The main half
 * fires onClick; the caret opens the options menu.
 *
 * @startingPoint section="Core" subtitle="Split action button — default action + options menu" viewport="700x150"
 */
export interface SplitButtonProps {
  /** Visual emphasis, shared by both halves. @default "primary" */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  /** Control height. @default "md" */
  size?: 'sm' | 'md' | 'lg'
  /** Disable both halves. @default false */
  disabled?: boolean
  /** Fires when the main half is clicked. */
  onClick?: () => void
  /** Alternatives shown in the caret menu. */
  options?: SplitButtonOption[]
  /** The currently active option value; marked with a check. */
  value?: string
  /** Fires with an option's value when it is chosen. */
  onSelect?: (value: string) => void
  /** Accessible label for the caret toggle. @default "Choose option" */
  menuLabel?: string
  children?: ReactNode
}

export function SplitButton(props: SplitButtonProps): JSX.Element
