import { ReactNode, HTMLAttributes } from 'react'

/**
 * Headline metric — big mono value with label, unit, trend delta and caption.
 * Used across dashboards (uptime, latency, volume, confidence).
 */
export interface MetricStatProps extends HTMLAttributes<HTMLDivElement> {
  /** Uppercase mono label. */
  label?: string
  /** The number / value (string or node). */
  value: ReactNode
  /** Small trailing unit (%, ms, etc.). */
  unit?: string
  /** Delta text shown beside the value (e.g. "+2.4%"). */
  delta?: ReactNode
  /** Direction — sets delta color + arrow. @default "flat" */
  trend?: 'up' | 'down' | 'flat'
  /** Caption line beneath. */
  caption?: string
  /** @default "md" */
  size?: 'sm' | 'md'
}

export function MetricStat(props: MetricStatProps): JSX.Element
