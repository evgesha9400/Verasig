import { HTMLAttributes } from 'react';

export interface TabItem {
  id: string;
  label: string;
  /** Optional count pill (e.g. number of signals). */
  count?: number;
}

/**
 * Tab bar for switching views. Controlled — pass `value` and `onChange`.
 * `line` variant for page-level navigation, `pill` for inline/segmented control.
 */
export interface TabsProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> {
  /** Tab definitions. Strings are shorthand for `{id, label}`. */
  items: (TabItem | string)[];
  /** Currently selected tab id. */
  value: string;
  /** Called with the new tab id. */
  onChange?: (id: string) => void;
  /** @default "line" */
  variant?: 'line' | 'pill';
}

export function Tabs(props: TabsProps): JSX.Element;
