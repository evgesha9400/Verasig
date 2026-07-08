import { HTMLAttributes } from 'react'

/**
 * Loading heartbeat. One family: a sweeping accent bar (canonical, pages /
 * sections) or a pulsing accent dot (tight inline spots). With `title`/`note`
 * it renders a centered block; with neither, a bare glyph for inline use.
 */
export interface LoaderProps extends HTMLAttributes<HTMLElement> {
  /** Glyph family. @default "bar" */
  variant?: 'bar' | 'dot'
  /** Glyph + block scale. @default "md" */
  size?: 'sm' | 'md' | 'lg'
  /** Bold title line. Omit for a bare inline glyph. */
  title?: string
  /** Secondary line under the title. */
  note?: string
}

export function Loader(props: LoaderProps): JSX.Element
