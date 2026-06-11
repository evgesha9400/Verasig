import { HTMLAttributes } from 'react';

/**
 * Avatar for users, providers and sources. Renders an image, or initials on a
 * tinted chip when no `src` is given. Optional status indicator dot.
 */
export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  /** Image URL. Falls back to initials when omitted. */
  src?: string;
  /** Full name — used for initials + alt text. */
  name?: string;
  /** @default "md" */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** Square (rounded) instead of circular — good for provider logos. */
  square?: boolean;
  /** Status dot: a known tone or any CSS color. */
  status?: 'verified' | 'pending' | 'rejected' | 'offline' | string;
  /** Background color for the initials chip. */
  tint?: string;
}

export function Avatar(props: AvatarProps): JSX.Element;
