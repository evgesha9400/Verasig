import { ReactNode } from 'react';

/**
 * Modal dialog with scrim, header (icon + title + description), body and footer.
 * Render it conditionally with `open`; clicking the scrim or × calls `onClose`.
 */
export interface DialogProps {
  /** Whether the dialog is visible. */
  open: boolean;
  /** Title line. */
  title?: string;
  /** Supporting description under the title. */
  description?: string;
  /** Header icon node. */
  icon?: ReactNode;
  /** Close handler (scrim click + × button). */
  onClose?: () => void;
  /** Footer node — typically the action buttons. */
  footer?: ReactNode;
  /** Body content. */
  children?: ReactNode;
}

export function Dialog(props: DialogProps): JSX.Element | null;
