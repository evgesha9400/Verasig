import { HTMLAttributes } from 'react'

/**
 * Confidence meter — shows a 0–100 verification score against the quorum
 * threshold. Color shifts red → amber → signal-green as it crosses threshold.
 * Set `segments` for a ticked/segmented variant.
 */
export interface ConfidenceBarProps extends HTMLAttributes<HTMLDivElement> {
  /** Score 0–100. */
  value: number
  /** Quorum threshold marker (0–100). @default 80 */
  threshold?: number
  /** Label text. @default "Confidence" */
  label?: string
  /** Show the numeric % value. @default true */
  showValue?: boolean
  /** Render N discrete segments instead of a continuous bar. @default 0 */
  segments?: number
}

export function ConfidenceBar(props: ConfidenceBarProps): JSX.Element
