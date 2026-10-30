import { HTMLAttributes } from 'react'

/**
 * Verification status pill with an icon — the canonical way to show a signal's
 * state. `pulse` adds a live ring for in-flight verification.
 */
export interface StatusPillProps extends HTMLAttributes<HTMLSpanElement> {
  /** Verification state. @default "pending" */
  status?: 'verified' | 'pending' | 'rejected' | 'observing'
  /** Override the default label text. */
  label?: string
  /** Animated pulse ring (live/in-flight). @default false */
  pulse?: boolean
}

export function StatusPill(props: StatusPillProps): JSX.Element
