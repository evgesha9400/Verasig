import { ReactNode, ButtonHTMLAttributes } from 'react';

/**
 * Verasig primary action button. Use for the single most important action in a
 * view (primary), supporting actions (secondary/ghost), and destructive flows (danger).
 *
 * @startingPoint section="Core" subtitle="Action button — primary, secondary, ghost, danger" viewport="700x150"
 */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual emphasis. @default "primary" */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  /** Control height. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** Icon node rendered before the label. */
  iconLeft?: ReactNode;
  /** Icon node rendered after the label. */
  iconRight?: ReactNode;
  /** Show a spinner and block interaction. @default false */
  loading?: boolean;
  /** Stretch to the width of the container. @default false */
  fullWidth?: boolean;
  /** Render as a different element (e.g. "a" for links). @default "button" */
  as?: 'button' | 'a';
  children?: ReactNode;
}

export function Button(props: ButtonProps): JSX.Element;
