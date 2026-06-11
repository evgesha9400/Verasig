import { ReactNode, HTMLAttributes } from 'react';

/**
 * Interactive tag / chip — filters, selected channels, providers. Optionally
 * shows a color swatch and a remove (×) affordance.
 */
export interface TagProps extends HTMLAttributes<HTMLSpanElement> {
  /** CSS color for a leading square swatch (e.g. a channel color). */
  swatch?: string;
  /** When provided, renders a × button; called on remove. */
  onRemove?: (e: React.MouseEvent) => void;
  /** Makes the whole tag clickable (filter toggle). */
  onClick?: (e: React.MouseEvent) => void;
  children?: ReactNode;
}

export function Tag(props: TagProps): JSX.Element;
