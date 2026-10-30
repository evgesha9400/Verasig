import { ReactNode, HTMLAttributes } from 'react'

/**
 * Inline banner / alert with a semantic tone, accent rail, icon and optional
 * dismiss + action buttons. Use for page-level or section-level messages.
 */
export interface BannerProps extends HTMLAttributes<HTMLDivElement> {
  /** Semantic tone. @default "info" */
  tone?: 'verified' | 'pending' | 'rejected' | 'info' | 'neutral'
  /** Bold title line. */
  title?: string
  /** Override the default tone icon. */
  icon?: ReactNode
  /** When set, shows a dismiss (×) button. */
  onClose?: () => void
  /** Action buttons row. */
  actions?: ReactNode
  /** Message body. */
  children?: ReactNode
}

export function Banner(props: BannerProps): JSX.Element
