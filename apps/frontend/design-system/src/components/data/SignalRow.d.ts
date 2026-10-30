import { HTMLAttributes } from 'react'

/**
 * Composite signal row — the core list item of the Verasig app. Shows the
 * symbol/event, source provider + channel, a confidence meter, verification
 * status and timestamp. Composes StatusPill + ConfidenceBar.
 *
 * @startingPoint section="Data" subtitle="Signal list row — confidence + verification status" viewport="700x90"
 */
export interface SignalRowProps extends HTMLAttributes<HTMLDivElement> {
  /** Symbol or event name, e.g. "BTC/USD" or "ELECTION-2028". */
  symbol: string
  /** Mono signal ID line under the symbol. */
  signalId?: string
  /** Source provider name. */
  provider: string
  /** Color for the provider chip. @default "var(--viz-2)" */
  providerTint?: string
  /** Channel label, e.g. "Webhook" or "gRPC · us-east". */
  channel?: string
  /** Confidence score 0–100. */
  confidence?: number
  /** Quorum threshold. @default 80 */
  threshold?: number
  /** Verification status. @default "pending" */
  status?: 'verified' | 'pending' | 'rejected' | 'observing'
  /** Mono timestamp. */
  time?: string
  /** Row click handler (makes the row interactive). */
  onClick?: () => void
}

export function SignalRow(props: SignalRowProps): JSX.Element
