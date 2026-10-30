import { ReactNode, HTMLAttributes } from 'react'

/**
 * Toast notification (presentational). Wire your own queue/timeout logic and
 * render toasts inside a `ToastStack`.
 */
export interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  /** Status tone — sets the leading dot color. @default "info" */
  tone?: 'verified' | 'pending' | 'rejected' | 'info'
  /** Title line. */
  title?: string
  /** Mono timestamp shown top-right. */
  time?: string
  /** Dismiss handler — shows a × when set. */
  onClose?: () => void
  /** Message body. */
  children?: ReactNode
}

export function Toast(props: ToastProps): JSX.Element

/** Fixed bottom-right stack container for toasts. */
export interface ToastStackProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode
}
export function ToastStack(props: ToastStackProps): JSX.Element
